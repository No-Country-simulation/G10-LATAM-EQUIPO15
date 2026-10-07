"""API interna: conserva el archivo original y delega su procesamiento a IA."""

import os
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.ai.schemas import AdaptacionContenidoResponse, NichoSectorEnum, PerfilDestinatarioEnum
from ia_http.runner import PipelineRunner, PipelineServiceError, get_pipeline_runner

MAX_DOCUMENT_BYTES = int(os.getenv("IA_MAX_DOCUMENT_BYTES", "10485760"))
if MAX_DOCUMENT_BYTES <= 0:
    raise ValueError("IA_MAX_DOCUMENT_BYTES debe ser positivo.")
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}
FormatoMVP = Literal["Flashcards", "Quiz Interactivo", "Resumen Ejecutivo", "Mapa Mental"]
pipeline_lock = Lock()


class ErrorDetail(BaseModel):
    codigo: str
    mensaje: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail


def error_detail(codigo: str, mensaje: str) -> dict:
    return {"codigo": codigo, "mensaje": mensaje}


app = FastAPI(title="NuevaMente — Servicio IA", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, _error):
    return JSONResponse(status_code=422, content={"detail": error_detail(
        "PARAMETROS_INVALIDOS", "Revisar documento_original, perfil_destinatario, formato_salida y nicho_sector."
    )})


@app.exception_handler(ResponseValidationError)
async def invalid_response(_request, _error):
    return JSONResponse(status_code=502, content={"detail": error_detail(
        "RESPUESTA_IA_INVALIDA", "IA produjo una respuesta que no cumple su esquema."
    )})


@app.get("/health", tags=["Health"])
def health():
    """Disponibilidad HTTP; no consulta Gemini ni valida la calidad del pipeline."""
    return {"status": "healthy", "service": "ia"}


@app.post(
    "/api/v1/adaptar-contenido",
    response_model=AdaptacionContenidoResponse,
    tags=["Adaptación"],
    summary="Adaptar un documento mediante el pipeline IA",
    responses={code: {"model": ErrorResponse} for code in (413, 415, 422, 500, 502, 503, 504)},
)
def adaptar_contenido(
    documento_original: Annotated[UploadFile, File(
        description="Archivo PDF, Markdown o TXT original.",
        json_schema_extra={"format": "binary"},
    )],
    perfil_destinatario: Annotated[PerfilDestinatarioEnum, Form()],
    formato_salida: Annotated[FormatoMVP, Form()],
    nicho_sector: Annotated[NichoSectorEnum, Form()],
    runner: Annotated[PipelineRunner, Depends(get_pipeline_runner)],
):
    # El pipeline síncrono hace operaciones bloqueantes y usa asyncio.run.
    # FastAPI ejecuta esta función en un hilo, separado del bucle HTTP.
    filename = (documento_original.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(415, error_detail("FORMATO_NO_SOPORTADO", "Utilizar PDF, Markdown o TXT."))
    if documento_original.size is not None and documento_original.size > MAX_DOCUMENT_BYTES:
        raise HTTPException(413, error_detail("DOCUMENTO_DEMASIADO_GRANDE", "El documento supera el límite de tamaño del servicio."))
    # El título es metadato derivado del nombre; nunca usamos ese nombre
    # como ruta del sistema de archivos ni modificamos los bytes recibidos.
    title = re.sub(r"[^A-Za-z0-9ÁÉÍÓÚáéíóúÑñ .,_-]", " ", Path(filename).stem).strip()[:150]
    if len(title) < 3:
        title = "Documento"
    if not pipeline_lock.acquire(blocking=False):
        raise HTTPException(503, error_detail("IA_OCUPADA", "IA está procesando otro documento. Reintentar más tarde."), headers={"Retry-After": "5"})
    try:
        with TemporaryDirectory(prefix="ia-http-") as temporary_directory:
            path = Path(temporary_directory) / f"documento{suffix}"
            total_bytes = 0
            with path.open("wb") as destination:
                while chunk := documento_original.file.read(65536):
                    total_bytes += len(chunk)
                    if total_bytes > MAX_DOCUMENT_BYTES:
                        raise HTTPException(413, error_detail("DOCUMENTO_DEMASIADO_GRANDE", "El documento supera el límite de tamaño del servicio."))
                    destination.write(chunk)
            if total_bytes == 0:
                raise HTTPException(422, error_detail("DOCUMENTO_VACIO", "El documento está vacío."))
            try:
                return runner(
                    documento_titulo=title,
                    ruta_archivo=str(path),
                    perfil=perfil_destinatario.value,
                    formato=formato_salida,
                    nicho=nicho_sector.value,
                    documento_nombre=filename,
                )
            except PipelineServiceError as error:
                raise HTTPException(error.status_code, error_detail(error.codigo, error.mensaje)) from error
    finally:
        pipeline_lock.release()
