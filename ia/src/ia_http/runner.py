"""Invoca el pipeline existente y traduce sus fallos a errores del servicio."""

import logging
import os
from collections.abc import Callable

import httpx
from google.genai.errors import APIError
from pydantic import ValidationError

from src.ai.pipeline import ejecutar_pipeline_adaptacion
from src.ai.schemas import AdaptacionContenidoResponse

logger = logging.getLogger(__name__)
PipelineRunner = Callable[..., AdaptacionContenidoResponse]


class PipelineServiceError(Exception):
    def __init__(self, status_code: int, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje


def _traducir_error(error: Exception) -> PipelineServiceError:
    # LangChain puede envolver el error del SDK. No exponemos su texto,
    # que podría contener URLs, claves, contenido o rutas temporales.
    current = error
    visited = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, (httpx.TimeoutException, TimeoutError)):
            return PipelineServiceError(504, "PROVEEDOR_TIMEOUT", "El proveedor de IA no respondió a tiempo.")
        if isinstance(current, APIError):
            status = current.code
            if status == 504:
                return PipelineServiceError(504, "PROVEEDOR_TIMEOUT", "El proveedor de IA no respondió a tiempo.")
            if status in (429, 503):
                return PipelineServiceError(503, "PROVEEDOR_NO_DISPONIBLE", "El proveedor de IA no está disponible o agotó su cuota.")
            return PipelineServiceError(502, "ERROR_PROVEEDOR", "El proveedor de IA no pudo completar la solicitud.")
        if isinstance(current, httpx.RequestError):
            return PipelineServiceError(503, "PROVEEDOR_NO_DISPONIBLE", "No se pudo contactar al proveedor de IA.")
        current = current.__cause__ or current.__context__

    if isinstance(error, ValidationError):
        return PipelineServiceError(502, "RESPUESTA_IA_INVALIDA", "IA produjo una respuesta que no cumple su esquema.")
    if isinstance(error, ValueError):
        message = str(error)
        if message.startswith("Contexto Insuficiente (Error 422):"):
            return PipelineServiceError(422, "CONTEXTO_INSUFICIENTE", "IA rechazó el contenido por no alcanzar su criterio de fidelidad.")
        if message.startswith("Error de Ingestión:"):
            return PipelineServiceError(422, "DOCUMENTO_RECHAZADO", "IA no pudo extraer contenido técnico suficiente del documento.")
        # Chunking y VectorStore devuelven mensajes sin preservar el tipo
        # de excepción original. No atribuimos estos fallos al usuario.
        if message.startswith(("Error de Chunking:", "Error de VectorStore:")):
            return PipelineServiceError(502, "ERROR_PROCESAMIENTO_IA", "IA no pudo segmentar o indexar el documento.")
    return PipelineServiceError(500, "ERROR_INTERNO_IA", "No se pudo completar el procesamiento en IA.")


def run_pipeline(**kwargs) -> AdaptacionContenidoResponse:
    if not os.getenv("GOOGLE_API_KEY") or not os.getenv("GEMINI_API_KEY"):
        raise PipelineServiceError(503, "IA_NO_CONFIGURADA", "Faltan las credenciales del servicio IA.")
    if os.getenv("IA_STRICT_PROVIDERS") != "1":
        raise PipelineServiceError(503, "IA_NO_CONFIGURADA", "El servicio IA requiere IA_STRICT_PROVIDERS=1.")
    try:
        result = ejecutar_pipeline_adaptacion(**kwargs)
        return AdaptacionContenidoResponse.model_validate(result)
    except Exception as error:
        logger.error("Fallo del pipeline IA: %s", type(error).__name__)
        raise _traducir_error(error) from error


def get_pipeline_runner() -> PipelineRunner:
    return run_pipeline
