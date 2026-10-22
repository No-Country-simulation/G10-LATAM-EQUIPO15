"""Catálogo privado por navegador, persistido en OCI y separado de objetos antiguos."""

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import logging
from pathlib import Path
import re
from uuid import uuid4

from fastapi import Depends
import oci
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.schemas import AdaptacionResponse, FormatoSalida, HistorialReferencia, NichoSector, PerfilDestinatario
from app.core.config import settings
from app.services.oci_service import OCIStorage, get_oci_storage, json_bytes

logger = logging.getLogger(__name__)
HASH = r"[a-f0-9]{64}"
ADAPTATION = r"[a-f0-9]{32}"


class HistoryError(Exception):
    def __init__(self, status=503, code="HISTORIAL_NO_DISPONIBLE", message="No se pudo consultar el historial. Reintentá más tarde."):
        self.status = status
        self.detail = {"codigo": code, "mensaje": message}


def missing():
    return HistoryError(404, "RECURSO_NO_ENCONTRADO", "El documento o resultado no está disponible en este historial.")


class DocumentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=f"^{HASH}$")
    nombre: str = Field(min_length=1, max_length=255)
    fecha: datetime
    tamano_bytes: int = Field(gt=0)
    tipo: str = Field(pattern=r"^\.(pdf|md|markdown|txt)$")
    objeto_original: str


class AdaptationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=f"^{ADAPTATION}$")
    documento_id: str = Field(pattern=f"^{HASH}$")
    fecha: datetime
    titulo: str
    perfil_destinatario: PerfilDestinatario
    formato_salida: FormatoSalida
    nicho_sector: NichoSector
    objeto_resultado: str


class AdaptationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    perfil_destinatario: PerfilDestinatario
    formato_salida: FormatoSalida
    nicho_sector: NichoSector


class HistoryStorage:
    def __init__(self, storage: OCIStorage):
        self.storage = storage

    def _prefix(self, owner):
        if not re.fullmatch(HASH, owner):
            raise missing()
        return f"historial-v1/{owner}/"

    def _document_key(self, owner, document_id):
        if not re.fullmatch(HASH, document_id):
            raise missing()
        return f"{self._prefix(owner)}documentos/{document_id}.json"

    def _files_prefix(self, owner):
        self._prefix(owner)
        return f"historial-archivos-v1/{owner}/"

    def _adaptation_prefix(self, owner, document_id):
        self._document_key(owner, document_id)
        return f"{self._prefix(owner)}adaptaciones/{document_id}/"

    def _adaptation_key(self, owner, document_id, adaptation_id):
        if not re.fullmatch(ADAPTATION, adaptation_id):
            raise missing()
        return f"{self._adaptation_prefix(owner, document_id)}{adaptation_id}.json"

    @contextmanager
    def _client(self):
        try:
            client = self.storage.client_factory()
            with client.base_client.session:
                yield client
        except HistoryError:
            raise
        except Exception as error:
            logger.warning("Historial OCI no disponible: %s", type(error).__name__)
            raise HistoryError() from error

    def _get(self, client, key, limit):
        try:
            response = client.get_object(self.storage.namespace, self.storage.bucket, key,
                                         retry_strategy=oci.retry.NoneRetryStrategy())
        except oci.exceptions.ServiceError as error:
            if error.status == 404:
                raise missing() from error
            raise
        if response.status != 200:
            raise HistoryError()
        with response.data:
            data = response.data.raw.read(limit + 1)
        if len(data) > limit:
            raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "El archivo guardado excede el tamaño permitido.")
        return data

    def _record(self, client, key, model):
        try:
            return model.model_validate_json(self._get(client, key, 65536))
        except (ValidationError, ValueError) as error:
            raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "No se pudo validar el registro guardado.") from error

    def register(self, owner, document, result):
        document.file.seek(0)
        source = document.file.read()
        document_id = sha256(source).hexdigest()
        name = (document.filename or "documento.txt").replace("\\", "/").rsplit("/", 1)[-1]
        name = re.sub(r"[\x00-\x1f\x7f]", "", name) or "documento.txt"
        suffix = Path(name).suffix.lower()
        name = name[:255 - len(suffix)] + suffix if len(name) > 255 else name
        now = datetime.now(timezone.utc)
        record = DocumentRecord(id=document_id, nombre=name, fecha=now, tamano_bytes=len(source),
                                tipo=Path(name).suffix.lower(), objeto_original=result.almacenamiento_oci.documento_original_objeto_id)
        adaptation = AdaptationRecord(id=uuid4().hex, documento_id=document_id, fecha=now,
            titulo=result.contenido_adaptado.titulo, perfil_destinatario=result.metadatos.perfil_aplicado,
            formato_salida=result.metadatos.formato_generado, nicho_sector=result.metadatos.nicho_contexto,
            objeto_resultado=result.almacenamiento_oci.objeto_id)
        with self._client() as client:
            self.storage._put(client, self._document_key(owner, document_id), json_bytes(record.model_dump(mode="json")), "application/json")
            self.storage._put(client, self._adaptation_key(owner, document_id, adaptation.id),
                              json_bytes(adaptation.model_dump(mode="json")), "application/json")
        return {"status": "disponible", "documento_id": document_id, "adaptacion_id": adaptation.id}

    def _list(self, client, prefix, model, cursor=None):
        if cursor and (not cursor.startswith(prefix) or len(cursor) > 1024):
            raise HistoryError(422, "PAGINACION_INVALIDA", "La página solicitada no es válida.")
        response = client.list_objects(self.storage.namespace, self.storage.bucket, prefix=prefix,
                                      start=cursor, limit=20, retry_strategy=oci.retry.NoneRetryStrategy())
        records = []
        for item in response.data.objects or []:
            if not item.name.endswith(".json"):
                continue
            record = self._record(client, item.name, model)
            if item.name != prefix + record.id + ".json":
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "El registro guardado no coincide con su identificador.")
            records.append(record)
        return records, response.data.next_start_with

    def documents(self, owner, cursor=None):
        with self._client() as client:
            records, next_cursor = self._list(client, self._prefix(owner) + "documentos/", DocumentRecord, cursor)
        return {"documentos": [r.model_dump(mode="json", exclude={"objeto_original"}) for r in records], "siguiente": next_cursor}

    def adaptations(self, owner, document_id, cursor=None):
        with self._client() as client:
            self._record(client, self._document_key(owner, document_id), DocumentRecord)
            records, next_cursor = self._list(client, self._adaptation_prefix(owner, document_id), AdaptationRecord, cursor)
            if any(r.documento_id != document_id for r in records):
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "El resultado no corresponde al documento.")
        return {"adaptaciones": [r.model_dump(mode="json", exclude={"objeto_resultado"}) for r in records], "siguiente": next_cursor}

    def original(self, owner, document_id):
        with self._client() as client:
            record = self._record(client, self._document_key(owner, document_id), DocumentRecord)
            if record.id != document_id or not re.fullmatch(rf"{self._files_prefix(owner)}documentos-fuente/\d{{4}}/\d{{2}}/{document_id}-[^/]+", record.objeto_original):
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "La referencia del original no es válida.")
            data = self._get(client, record.objeto_original, settings.MAX_DOCUMENT_BYTES)
            if len(data) != record.tamano_bytes or sha256(data).hexdigest() != document_id:
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "El original guardado no superó la comprobación de integridad.")
        return record, data

    def result(self, owner, document_id, adaptation_id):
        with self._client() as client:
            doc = self._record(client, self._document_key(owner, document_id), DocumentRecord)
            record = self._record(client, self._adaptation_key(owner, document_id, adaptation_id), AdaptationRecord)
            if (doc.id != document_id or record.id != adaptation_id or record.documento_id != document_id
                or not re.fullmatch(rf"{self._files_prefix(owner)}artefactos-generados/\d{{4}}/\d{{2}}/{document_id}-{HASH}-[a-f0-9]{{16}}\.json", record.objeto_resultado)):
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "La referencia del resultado no es válida.")
            try:
                result = AdaptacionResponse.model_validate_json(self._get(client, record.objeto_resultado, 8 * 1024 * 1024))
            except ValidationError as error:
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "No se pudo validar el resultado guardado.") from error
            metadata, stored = result.metadatos, result.almacenamiento_oci
            artifact_hash = sha256(json_bytes(result.model_dump(mode="json", exclude_unset=True,
                                                                exclude={"almacenamiento_oci", "historial"}))).hexdigest()
            if ((metadata.perfil_aplicado, metadata.formato_generado, metadata.nicho_contexto)
                != (record.perfil_destinatario, record.formato_salida, record.nicho_sector)
                or stored.status_upload != "subido" or stored.documento_original_subido is not True
                or stored.objeto_id != record.objeto_resultado
                or not record.objeto_resultado.endswith(f"-{artifact_hash}-{sha256((stored.documento_original_objeto_id or '').encode()).hexdigest()[:16]}.json")
                or not re.fullmatch(rf"{self._files_prefix(owner)}documentos-fuente/\d{{4}}/\d{{2}}/{document_id}-[^/]+", stored.documento_original_objeto_id or "")):
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "El resultado guardado no coincide con su registro.")
        return result.model_copy(update={"historial": HistorialReferencia(status="disponible", documento_id=document_id, adaptacion_id=adaptation_id)})


def get_history_storage(storage: OCIStorage | None = Depends(get_oci_storage)) -> HistoryStorage | None:
    return HistoryStorage(storage) if storage is not None and settings.HISTORY_ENABLED else None
