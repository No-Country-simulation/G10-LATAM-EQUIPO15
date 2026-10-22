import os
import logging
from io import BytesIO
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.datastructures import Headers
from app.core.config import settings
from app.api.schemas import AdaptacionResponse, ErrorResponse, FormatoSalida, HistorialReferencia, NichoSector, PerfilDestinatario
from app.services.ia_client import IAClient, IAServiceError, get_ia_client
from app.services.oci_service import OCIStorage, get_oci_storage
from app.services.browser_identity import browser_identity
from app.services.history_service import AdaptationConfig, HistoryError, HistoryStorage, get_history_storage
from app.services.oci_service import json_bytes

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs"
)
app.middleware("http")(browser_identity)


@app.exception_handler(HistoryError)
async def history_error(_request, error):
    return JSONResponse(status_code=error.status, content={"detail": error.detail}, headers={"Cache-Control": "no-store"})

@app.get("/")
def read_root():
    return {"message": "API de NuevaMente en ejecución", "status": "ok"}

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "backend"
    }

@app.exception_handler(RequestValidationError)
async def invalid_request(_request, _error):
    return JSONResponse(status_code=422, content={"detail": {
        "codigo": "PARAMETROS_INVALIDOS",
        "mensaje": "Revisar documento_original, perfil_destinatario, formato_salida y nicho_sector.",
    }})


@app.exception_handler(Exception)
async def generic_backend_exception(_request, error):
    if isinstance(error, HTTPException):
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail}, headers=error.headers)
    return JSONResponse(status_code=500, content={"detail": {
        "codigo": "ERROR_INTERNO_BACKEND",
        "mensaje": "Error interno del servidor en Backend."
    }})


@app.post(
    f"{settings.API_V1_STR}/adaptar-contenido",
    response_model=AdaptacionResponse,
    response_model_exclude_unset=True,
    status_code=status.HTTP_200_OK,
    summary="Adaptar un documento mediante el servicio IA",
    description="Envía el archivo original y sus parámetros al servicio IA.",
    responses={code: {"model": ErrorResponse} for code in (413, 415, 422, 500, 502, 503, 504)},
)
def adaptar_contenido(
    request: Request,
    documento_original: Annotated[UploadFile, File(
        description="Documento original PDF, Markdown o TXT.", json_schema_extra={"format": "binary"},
    )],
    perfil_destinatario: Annotated[PerfilDestinatario, Form()],
    formato_salida: Annotated[FormatoSalida, Form()],
    nicho_sector: Annotated[NichoSector, Form()],
    ia_client: Annotated[IAClient, Depends(get_ia_client)],
    oci_storage: Annotated[OCIStorage | None, Depends(get_oci_storage)],
    history: Annotated[HistoryStorage | None, Depends(get_history_storage)],
):
    """Valida el transporte y delega extracción, generación y calidad a IA."""
    return _adaptar_y_guardar(request, documento_original, perfil_destinatario, formato_salida, nicho_sector,
                             ia_client, oci_storage, history)


def _adaptar_y_guardar(request, documento_original, perfil_destinatario, formato_salida, nicho_sector,
                      ia_client, oci_storage, history):
    if history is not None and request.state.history_identity_new:
        raise HTTPException(409, {"codigo": "HISTORIAL_IDENTIDAD_REQUERIDA",
                                 "mensaje": "Prepará el historial antes de generar. Volvé a intentar la solicitud."})
    filename = (documento_original.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if Path(filename).suffix.lower() not in {".pdf", ".md", ".markdown", ".txt"}:
        raise HTTPException(415, {"codigo": "FORMATO_NO_SOPORTADO", "mensaje": "Utilizar PDF, Markdown o TXT."})
    documento_original.file.seek(0, os.SEEK_END)
    size = documento_original.file.tell()
    documento_original.file.seek(0)
    if size > settings.MAX_DOCUMENT_BYTES:
        raise HTTPException(413, {"codigo": "DOCUMENTO_DEMASIADO_GRANDE", "mensaje": "El documento supera el límite de tamaño del Backend."})
    if size == 0:
        raise HTTPException(422, {"codigo": "DOCUMENTO_VACIO", "mensaje": "El documento está vacío."})
    try:
        resultado = ia_client.adaptar(documento_original, perfil_destinatario.value, formato_salida.value, nicho_sector.value)
    except IAServiceError as error:
        raise HTTPException(error.status_code, error.detail, headers=error.headers) from error
    if oci_storage is not None:
        resultado = oci_storage.guardar(documento_original, resultado,
                                        scope=request.state.history_owner if history is not None else None)
    if history is not None:
        reference = HistorialReferencia(status="error", mensaje="El resultado está disponible, pero no se confirmó su registro en el historial.")
        stored = resultado.almacenamiento_oci
        if stored.status_upload == "subido" and stored.documento_original_subido is True:
            try:
                reference = HistorialReferencia(**history.register(request.state.history_owner, documento_original, resultado))
            except Exception as error:
                logger.warning("No se confirmó el registro del historial: %s", type(error).__name__)
        resultado = resultado.model_copy(update={"historial": reference})
    return resultado


def require_history(history: Annotated[HistoryStorage | None, Depends(get_history_storage)]) -> HistoryStorage:
    if history is None:
        raise HistoryError(message="El historial necesita almacenamiento OCI habilitado. Podés seguir generando contenido.")
    return history


History = Annotated[HistoryStorage, Depends(require_history)]


@app.get(f"{settings.API_V1_STR}/historial/sesion", tags=["Historial"])
def prepare_history(storage: Annotated[OCIStorage | None, Depends(get_oci_storage)]):
    # Establece la identidad sin depender de consultas a OCI ni invocar IA.
    return {"habilitado": storage is not None and settings.HISTORY_ENABLED}


@app.get(f"{settings.API_V1_STR}/documentos", tags=["Historial"])
def list_documents(request: Request, history: History, cursor: str | None = None):
    return history.documents(request.state.history_owner, cursor)


@app.get(f"{settings.API_V1_STR}/documentos/{{document_id}}/adaptaciones", tags=["Historial"])
def list_adaptations(document_id: str, request: Request, history: History, cursor: str | None = None):
    return history.adaptations(request.state.history_owner, document_id, cursor)


@app.get(f"{settings.API_V1_STR}/documentos/{{document_id}}/original", tags=["Historial"])
def download_original(document_id: str, request: Request, history: History):
    record, data = history.original(request.state.history_owner, document_id)
    return Response(data, media_type="application/octet-stream", headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(record.nombre, safe='')}",
    })


@app.get(f"{settings.API_V1_STR}/documentos/{{document_id}}/adaptaciones/{{adaptation_id}}", response_model=AdaptacionResponse,
         response_model_exclude_unset=True, tags=["Historial"])
def open_adaptation(document_id: str, adaptation_id: str, request: Request, history: History):
    return history.result(request.state.history_owner, document_id, adaptation_id)


@app.get(f"{settings.API_V1_STR}/documentos/{{document_id}}/adaptaciones/{{adaptation_id}}/descarga", tags=["Historial"])
def download_adaptation(document_id: str, adaptation_id: str, request: Request, history: History):
    result = history.result(request.state.history_owner, document_id, adaptation_id)
    return Response(json_bytes(result.model_dump(mode="json", exclude_unset=True)), media_type="application/json", headers={
        "Content-Disposition": f'attachment; filename="adaptacion-{adaptation_id}.json"',
    })


@app.post(f"{settings.API_V1_STR}/documentos/{{document_id}}/adaptaciones", response_model=AdaptacionResponse,
          response_model_exclude_unset=True, tags=["Historial"])
def adapt_saved(document_id: str, config: AdaptationConfig, request: Request, history: History,
                ia_client: Annotated[IAClient, Depends(get_ia_client)],
                storage: Annotated[OCIStorage | None, Depends(get_oci_storage)]):
    record, data = history.original(request.state.history_owner, document_id)
    upload = UploadFile(filename=record.nombre, file=BytesIO(data), headers=Headers({"content-type":
                        "application/pdf" if record.tipo == ".pdf" else "text/plain; charset=utf-8"}))
    try:
        return _adaptar_y_guardar(request, upload, config.perfil_destinatario, config.formato_salida,
                                 config.nicho_sector, ia_client, storage, history)
    finally:
        upload.file.close()
