"""Límites y observabilidad comunes a las llamadas reales del proveedor."""

import logging
import math
import os
import time
from contextlib import contextmanager

import httpx
from google.genai import types
from google.genai.errors import APIError
from langchain_core.callbacks import BaseCallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)


def provider_limits() -> tuple[float, int]:
    timeout = float(os.getenv("IA_PROVIDER_TIMEOUT_SECONDS", "60"))
    retries = int(os.getenv("IA_PROVIDER_MAX_RETRIES", "1"))
    if not math.isfinite(timeout) or timeout <= 0 or not 0 <= retries <= 2:
        raise ValueError("Configuración inválida de límites del proveedor.")
    return timeout, retries


def provider_http_options() -> types.HttpOptions:
    timeout, retries = provider_limits()
    return types.HttpOptions(
        timeout=max(1, int(timeout * 1000)),
        retry_options=types.HttpRetryOptions(
            attempts=retries + 1, initial_delay=1, max_delay=5,
        ),
    )


class _RegistroFallosModelo(BaseCallbackHandler):
    """
    Registra cada modelo que falla dentro de una cadena de respaldo. Sin esto, si todos
    fallan solo se ve el error del principal y se pierde la causa real de cada respaldo.
    """

    def __init__(self, modelo: str):
        self.modelo = modelo

    def on_llm_error(self, error, **kwargs):
        kind, code, category = safe_error_fields(error)
        logger.warning("IA modelo=%s estado=fallo tipo=%s codigo=%s categoria=%s", self.modelo, kind, code, category)


def create_gemini_llm(temperature: float = 0.0, *, api_key: str | None = None, model: str | None = None):
    timeout, retries = provider_limits()
    model = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    # Google recomienda el valor predeterminado para Gemini 3. LangChain
    # deja temperature=None para esta familia y el SDK usa el default.
    temperature_options = {} if model.removeprefix("models/").startswith("gemini-3") else {"temperature": temperature}
    # En langchain-google-genai 4.4, max_retries se transmite al SDK como
    # número de intentos totales. Convertimos los reintentos configurados.
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        **temperature_options,
        timeout=timeout,
        max_retries=retries + 1,
        callbacks=[_RegistroFallosModelo(model)],
    )


def error_chain(error: Exception):
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        yield error
        error = error.__cause__ or error.__context__


def is_provider_error(error: Exception) -> bool:
    return any(isinstance(e, (APIError, httpx.RequestError, TimeoutError)) for e in error_chain(error))


def safe_error_fields(error: Exception) -> tuple[str, int | None, str]:
    for current in error_chain(error):
        if isinstance(current, APIError):
            code = current.code if isinstance(current.code, int) else None
            category = {429: "cuota", 503: "indisponibilidad", 504: "timeout"}.get(code, "proveedor")
            return type(current).__name__, code, category
        if isinstance(current, (httpx.TimeoutException, TimeoutError)):
            return type(current).__name__, None, "timeout"
        if isinstance(current, httpx.RequestError):
            return type(current).__name__, None, "comunicacion"
        status = getattr(current, "status_code", None)  # errores del SDK de Groq
        if isinstance(status, int):
            return type(current).__name__, status, {413: "tamano", 429: "cuota", 503: "indisponibilidad"}.get(status, "proveedor")
    return type(error).__name__, None, "interno"


@contextmanager
def provider_call(stage: str):
    started = time.monotonic()
    logger.info("IA proveedor etapa=%s estado=inicio", stage)
    try:
        yield
    except Exception as error:
        kind, code, category = safe_error_fields(error)
        logger.error(
            "IA proveedor etapa=%s estado=fallo tipo=%s codigo=%s categoria=%s segundos=%.2f",
            stage, kind, code, category, time.monotonic() - started,
        )
        raise
    else:
        logger.info("IA proveedor etapa=%s estado=fin segundos=%.2f", stage, time.monotonic() - started)


def gemini_fallback_models() -> list[str]:
    """
    Modelos Gemini de respaldo, separados por coma. Cada modelo tiene su propia cuota
    gratuita: ante un 503 (sobrecarga) o 429 del principal, se reintenta con el siguiente.
    """
    valor = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.1-flash-lite")
    principal = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    return [m.strip() for m in valor.split(",") if m.strip() and m.strip() != principal]


def create_groq_llm(temperature: float, model: str):
    from langchain_groq import ChatGroq

    class ChatGroqEsquemaJSON(ChatGroq):
        # Con prompts largos, la salida estructurada por llamada a herramientas fallaba en los
        # tres modelos gratuitos ('tool_use_failed'); con esquema JSON respondieron bien.
        def with_structured_output(self, schema, *, method="json_schema", **kwargs):
            return super().with_structured_output(schema, method=method, **kwargs)

    timeout, retries = provider_limits()
    # Groq gratuito: 8.000 tokens por minuto por modelo, contando la salida máxima reservada.
    # Los gpt-oss razonan antes de responder: sin limitarlo, el razonamiento agotaba la salida
    # antes de completar el JSON ('json_validate_failed'). Un tope explícito reduce la reserva.
    extra = {"reasoning_effort": "low"} if model.startswith("openai/gpt-oss") else {}
    return ChatGroqEsquemaJSON(model=model, api_key=os.getenv("GROQ_API_KEY"), temperature=temperature,
                               timeout=timeout, max_retries=retries, callbacks=[_RegistroFallosModelo(model)],
                               max_tokens=int(os.getenv("GROQ_MAX_TOKENS", "2500")), **extra)


def with_fallback_chain(primary, fallbacks: list):
    """Encadena respaldos; si todos fallan se propaga el error del principal."""
    return primary.with_fallbacks(fallbacks) if fallbacks else primary
