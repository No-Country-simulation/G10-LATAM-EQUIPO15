"""Cliente HTTP de IA: transporta el archivo original sin extraer su texto."""

import logging

import httpx
from pydantic import ValidationError

from app.api.schemas import AdaptacionResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

# Los mensajes son locales y estables: no devolvemos texto de excepciones
# ni cuerpos arbitrarios recibidos del servicio remoto.
IA_ERRORS = {
    "PARAMETROS_INVALIDOS": (422, "Los parámetros enviados a IA son inválidos."),
    "DOCUMENTO_VACIO": (422, "El documento está vacío."),
    "FORMATO_NO_SOPORTADO": (415, "Utilizar PDF, Markdown o TXT."),
    "DOCUMENTO_DEMASIADO_GRANDE": (413, "El documento supera el límite de tamaño del servicio IA."),
    "IA_OCUPADA": (503, "IA está procesando otro documento. Reintentar más tarde."),
    "IA_NO_CONFIGURADA": (503, "El servicio IA no está configurado para procesar solicitudes."),
    "CONTEXTO_INSUFICIENTE": (422, "IA rechazó el contenido por no alcanzar su criterio de fidelidad."),
    "DOCUMENTO_RECHAZADO": (422, "IA no pudo extraer contenido técnico suficiente del documento."),
    "PROVEEDOR_TIMEOUT": (504, "El proveedor de IA no respondió a tiempo."),
    "PROVEEDOR_NO_DISPONIBLE": (503, "El proveedor de IA no está disponible o agotó su cuota."),
    "ERROR_PROVEEDOR": (502, "El proveedor de IA no pudo completar la solicitud."),
    "RESPUESTA_IA_INVALIDA": (502, "IA produjo una respuesta que no cumple su esquema."),
    "ERROR_PROCESAMIENTO_IA": (502, "IA no pudo segmentar o indexar el documento."),
    "ERROR_INTERNO_IA": (500, "No se pudo completar el procesamiento en IA."),
}


class IAServiceError(Exception):
    def __init__(self, status_code: int, codigo: str, mensaje: str, headers: dict | None = None):
        super().__init__(mensaje)
        self.status_code = status_code
        self.detail = {"codigo": codigo, "mensaje": mensaje}
        self.headers = headers or {}


def invalid_response() -> IAServiceError:
    return IAServiceError(502, "RESPUESTA_IA_INVALIDA", "IA produjo una respuesta que no cumple su esquema.")


class IAClient:
    def __init__(self, base_url: str, timeout_seconds: float, transport=None):
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def adaptar(self, documento_original, perfil: str, formato: str, nicho: str) -> AdaptacionResponse:
        documento_original.file.seek(0)
        filename = (documento_original.filename or "documento").replace("\\", "/").rsplit("/", 1)[-1]
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout_seconds, connect=5.0, pool=5.0),
                transport=self.transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = client.post(
                    "/api/v1/adaptar-contenido",
                    data={"perfil_destinatario": perfil, "formato_salida": formato, "nicho_sector": nicho},
                    files={"documento_original": (
                        filename, documento_original.file,
                        documento_original.content_type or "application/octet-stream",
                    )},
                )
        except httpx.TimeoutException as error:
            raise IAServiceError(504, "IA_TIMEOUT", "IA no respondió dentro del tiempo configurado.") from error
        except httpx.RequestError as error:
            logger.error("Fallo de comunicación con IA: %s", type(error).__name__)
            raise IAServiceError(503, "IA_NO_DISPONIBLE", "No se pudo contactar al servicio IA.") from error

        try:
            payload = response.json()
        except ValueError as error:
            raise invalid_response() from error
        if response.status_code != 200:
            detail = payload.get("detail") if isinstance(payload, dict) else None
            codigo = detail.get("codigo") if isinstance(detail, dict) else None
            mapped = IA_ERRORS.get(codigo) if isinstance(codigo, str) else None
            if mapped is None or mapped[0] != response.status_code:
                raise invalid_response()
            retry_after = response.headers.get("retry-after", "")
            headers = {}
            if response.status_code == 503 and retry_after.isascii() and retry_after.isdigit() and len(retry_after) <= 4:
                if 0 < int(retry_after) <= 3600:
                    headers["Retry-After"] = retry_after
            raise IAServiceError(response.status_code, codigo, mapped[1], headers)
        try:
            result = AdaptacionResponse.model_validate(payload)
        except ValidationError as error:
            raise invalid_response() from error
        metadata = result.metadatos
        if (metadata.perfil_aplicado.value, metadata.formato_generado.value, metadata.nicho_contexto.value) != (perfil, formato, nicho):
            raise invalid_response()
        return result


def get_ia_client() -> IAClient:
    return IAClient(settings.IA_BASE_URL, settings.IA_HTTP_TIMEOUT_SECONDS)
