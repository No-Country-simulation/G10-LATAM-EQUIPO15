"""Persistencia dual opcional: original y JSON aprobado, sin exponer objetos públicos."""

import base64
from datetime import datetime, timezone
from hashlib import md5, sha256
from io import BytesIO
import json
import logging
from pathlib import Path
import re

import oci

from app.api.schemas import AdaptacionResponse, AlmacenamientoOCI
from app.core.config import settings

logger = logging.getLogger(__name__)


def create_oci_client():
    options = {
        "timeout": (5, settings.OCI_HTTP_TIMEOUT_SECONDS),
        "retry_strategy": oci.retry.NoneRetryStrategy(),
    }
    if settings.OCI_AUTH_MODE == "instance_principal":
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner(
            federation_client_retry_strategy=oci.retry.NoneRetryStrategy(),
        )
        return oci.object_storage.ObjectStorageClient(
            {"region": settings.OCI_REGION}, signer=signer, **options,
        )
    config = oci.config.from_file(settings.OCI_CONFIG_FILE, settings.OCI_CONFIG_PROFILE)
    if settings.OCI_REGION:
        config["region"] = settings.OCI_REGION
    return oci.object_storage.ObjectStorageClient(config, **options)


def json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class OCIStorage:
    def __init__(self, namespace: str, bucket: str, client_factory=create_oci_client, clock=None):
        self.namespace = namespace
        self.bucket = bucket
        self.client_factory = client_factory
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def guardar(self, documento, resultado: AdaptacionResponse) -> AdaptacionResponse:
        # IA puede haber consumido el stream. Persistimos exactamente el original.
        documento.file.seek(0)
        original = documento.file.read()
        digest = sha256(original).hexdigest()
        filename = (documento.filename or "documento.txt").replace("\\", "/").rsplit("/", 1)[-1]
        suffix = Path(filename).suffix.lower()
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(filename).stem).strip("_")[:64] or "documento"
        period = self.clock().strftime("%Y/%m")
        source_key = f"documentos-fuente/{period}/{digest}-{stem}{suffix}"
        # Ignoramos los nombres de objetos propuestos por IA. El Backend los asigna.
        content = resultado.model_dump(mode="json", exclude_unset=True, exclude={"almacenamiento_oci"})
        artifact_digest = sha256(json_bytes(content)).hexdigest()
        artifact_key = f"artefactos-generados/{period}/{digest}-{artifact_digest}.json"
        stored = resultado.model_copy(update={"almacenamiento_oci": AlmacenamientoOCI(
            bucket=self.bucket, objeto_id=artifact_key, status_upload="subido",
            ruta_publica_o_par=None, documento_original_objeto_id=source_key,
            documento_original_subido=True,
        )})
        source_confirmed = False
        stage = "configuracion"
        try:
            client = self.client_factory()
            with client.base_client.session:
                stage = "documento"
                self._put(client, source_key, original, "application/pdf" if suffix == ".pdf" else "text/plain; charset=utf-8")
                source_confirmed = True
                stage = "json"
                self._put(client, artifact_key, json_bytes(stored.model_dump(mode="json", exclude_unset=True)), "application/json; charset=utf-8")
        except Exception as error:
            # Dos objetos no forman una transacción: un fallo puede dejar solo el original.
            # Un timeout tampoco prueba que el servidor no haya guardado el objeto.
            code = "OCI_NO_CONFIGURADO" if stage == "configuracion" else "OCI_NO_DISPONIBLE"
            if isinstance(error, oci.exceptions.ServiceError) and error.status in {401, 403}:
                code = "OCI_ACCESO_DENEGADO"
            logger.warning("Persistencia OCI no confirmada: etapa=%s tipo=%s", stage, type(error).__name__)
            return resultado.model_copy(update={"almacenamiento_oci": AlmacenamientoOCI(
                bucket=self.bucket, objeto_id=artifact_key,
                status_upload="parcial" if source_confirmed else "error", ruta_publica_o_par=None,
                documento_original_objeto_id=source_key, documento_original_subido=source_confirmed,
                codigo_error=code, mensaje="No se pudo confirmar la subida completa a OCI. El contenido generado se conserva.",
            )})
        return stored

    def _put(self, client, key, data, content_type):
        response = client.put_object(
            self.namespace, self.bucket, key, BytesIO(data),
            content_length=len(data), content_type=content_type,
            content_md5=base64.b64encode(md5(data, usedforsecurity=False).digest()).decode("ascii"),
            retry_strategy=oci.retry.NoneRetryStrategy(),
        )
        if response.status != 200:
            raise RuntimeError("OCI no confirmó la operación PutObject.")


def get_oci_storage() -> OCIStorage | None:
    if not settings.OCI_STORAGE_ENABLED:
        return None
    return OCIStorage(settings.OCI_NAMESPACE, settings.OCI_BUCKET_NAME)
