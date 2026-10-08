"""Invoca el pipeline existente y traduce sus fallos a errores del servicio."""

import logging
import math
import multiprocessing
import os
import re
import time
from collections.abc import Callable

import httpx
from google.genai.errors import APIError
from pydantic import ValidationError

from src.ai.pipeline import ejecutar_pipeline_adaptacion
from src.ai.schemas import AdaptacionContenidoResponse
from dataia.common.providers import provider_limits, safe_error_fields

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
    started = time.monotonic()
    stage = "INICIO"
    original_callback = kwargs.pop("callback_telemetria", None)

    def telemetry(etapa, paso, progreso, mensaje):
        nonlocal stage
        # El callback no registra el mensaje: puede contener datos del usuario.
        stage = etapa if etapa in {"EXTRACCION", "INDEXACION", "GENERACION", "AUDITORIA", "COMPLETADO"} else "PIPELINE"
        logger.info("IA pipeline etapa=%s segundos=%.2f", stage, time.monotonic() - started)
        if stage == "AUDITORIA":
            score = re.search(r"Fidelidad evaluada \(([0-9.]+)\)", mensaje)
            if score:
                logger.info("IA pipeline fidelidad=%s", score.group(1))
        if original_callback:
            original_callback(etapa, paso, progreso, mensaje)

    try:
        kwargs["callback_telemetria"] = telemetry
        result = ejecutar_pipeline_adaptacion(**kwargs)
        return AdaptacionContenidoResponse.model_validate(result)
    except Exception as error:
        kind, code, category = safe_error_fields(error)
        logger.error(
            "Fallo del pipeline IA: etapa=%s tipo=%s codigo=%s categoria=%s segundos=%.2f",
            stage, kind, code, category, time.monotonic() - started,
        )
        raise _traducir_error(error) from error


def _pipeline_worker(connection, kwargs):
    """Proceso aislado: solo transmite el resultado o un error público seguro."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")
    logger.setLevel(logging.INFO)
    logging.getLogger("dataia.common.providers").setLevel(logging.INFO)
    try:
        result = run_pipeline(**kwargs)
        connection.send({"result": result.model_dump(mode="json")})
    except PipelineServiceError as error:
        connection.send({"error": (error.status_code, error.codigo, error.mensaje)})
    except Exception as error:
        kind, code, category = safe_error_fields(error)
        logger.error("Fallo del worker IA: tipo=%s codigo=%s categoria=%s", kind, code, category)
        connection.send({"error": (500, "ERROR_INTERNO_IA", "No se pudo completar el procesamiento en IA.")})
    finally:
        connection.close()


def _run_in_process(worker, kwargs, budget: float) -> AdaptacionContenidoResponse:
    """Una espera global real; al vencer termina el proceso y sus llamadas."""
    context = multiprocessing.get_context("spawn")
    receiving, sending = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(sending, kwargs), daemon=True)
    started = time.monotonic()
    try:
        process.start()
        sending.close()
        remaining = max(0, budget - (time.monotonic() - started))
        if not receiving.poll(remaining):
            logger.error("IA pipeline estado=timeout_global limite_segundos=%.2f", budget)
            raise PipelineServiceError(504, "PROVEEDOR_TIMEOUT", "IA agotó el tiempo total de procesamiento.")
        try:
            packet = receiving.recv()
        except EOFError:
            raise PipelineServiceError(500, "ERROR_INTERNO_IA", "El procesamiento de IA se interrumpió.") from None
        if "error" in packet:
            raise PipelineServiceError(*packet["error"])
        return AdaptacionContenidoResponse.model_validate(packet["result"])
    finally:
        receiving.close()
        sending.close()
        if process.pid is not None:
            process.join(timeout=0.2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            process.close()


def run_pipeline_with_deadline(**kwargs) -> AdaptacionContenidoResponse:
    try:
        budget = float(os.getenv("IA_PIPELINE_TIMEOUT_SECONDS", "480"))
        caller_budget = float(os.getenv("IA_CALLER_TIMEOUT_SECONDS", "600"))
        provider_limits()
        if not math.isfinite(budget) or budget <= 0 or not math.isfinite(caller_budget) or budget >= caller_budget - 5:
            raise ValueError("Presupuesto de tiempo inválido.")
    except (ValueError, OverflowError):
        raise PipelineServiceError(503, "IA_NO_CONFIGURADA", "Revisar los límites de tiempo y reintentos de IA.") from None
    if not os.getenv("GOOGLE_API_KEY") or not os.getenv("GEMINI_API_KEY") or os.getenv("IA_STRICT_PROVIDERS") != "1":
        raise PipelineServiceError(503, "IA_NO_CONFIGURADA", "Revisar las credenciales y el modo estricto de IA.")
    return _run_in_process(_pipeline_worker, kwargs, budget)


def get_pipeline_runner() -> PipelineRunner:
    return run_pipeline_with_deadline
