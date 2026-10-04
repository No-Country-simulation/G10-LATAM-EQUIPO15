import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.schemas import AdaptacionResponse, ErrorResponse, FormatoSalida, NichoSector, PerfilDestinatario
from app.services.ia_client import IAClient, IAServiceError, get_ia_client

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs"
)

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
    documento_original: Annotated[UploadFile, File(
        description="Documento original PDF, Markdown o TXT.", json_schema_extra={"format": "binary"},
    )],
    perfil_destinatario: Annotated[PerfilDestinatario, Form()],
    formato_salida: Annotated[FormatoSalida, Form()],
    nicho_sector: Annotated[NichoSector, Form()],
    ia_client: Annotated[IAClient, Depends(get_ia_client)],
):
    """Valida el transporte y delega extracción, generación y calidad a IA."""
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
        return ia_client.adaptar(documento_original, perfil_destinatario.value, formato_salida.value, nicho_sector.value)
    except IAServiceError as error:
        raise HTTPException(error.status_code, error.detail, headers=error.headers) from error
