"""Catálogo privado por navegador, persistido en OCI y separado de objetos antiguos."""

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from functools import wraps
import logging
from pathlib import Path
import re
from uuid import uuid4
from threading import RLock
from typing import Literal

from fastapi import Depends
import oci
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.schemas import AdaptacionResponse, FormatoSalida, HistorialReferencia, NichoSector, PerfilDestinatario
from app.core.config import settings
from app.services.oci_service import OCIStorage, get_oci_storage, json_bytes

logger = logging.getLogger(__name__)
HASH = r"[a-f0-9]{64}"
ADAPTATION = r"[a-f0-9]{32}"
# El despliegue MVP usa un único worker. Las franjas acotan la memoria de locks.
_LOCKS = tuple(RLock() for _ in range(128))


def synchronized(method):
    @wraps(method)
    def call(self, owner, *args, **kwargs):
        with self.lock(owner):
            return method(self, owner, *args, **kwargs)
    return call


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


class DeletionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: Literal["pendiente", "completado"] = "pendiente"
    fecha: datetime
    version: str = Field(pattern=f"^{HASH}$")
    cantidad: int = Field(ge=0)
    documento: DocumentRecord | None = None
    adaptacion: AdaptationRecord | None = None


class HistoryStorage:
    def __init__(self, storage: OCIStorage):
        self.storage = storage

    def lock(self, owner):
        self._prefix(owner)
        return _LOCKS[int(owner[:8], 16) % len(_LOCKS)]

    def _deletion_key(self, owner, document_id, adaptation_id=None):
        self._document_key(owner, document_id)
        if adaptation_id is not None:
            self._adaptation_key(owner, document_id, adaptation_id)
            return f"{self._deletions_prefix(owner)}adaptaciones/{document_id}/{adaptation_id}.json"
        return f"{self._deletions_prefix(owner)}documentos/{document_id}.json"

    def _deletions_prefix(self, owner):
        self._prefix(owner)
        return f"historial-control-v1/{owner}/eliminaciones/"

    def _optional(self, client, key, model):
        try:
            return self._record(client, key, model)
        except HistoryError as error:
            if error.status == 404:
                return None
            raise

    def _pending(self, client, owner, document_id, adaptation_id=None):
        record = self._optional(client, self._deletion_key(owner, document_id, adaptation_id), DeletionRecord)
        return record if record is not None and record.estado == "pendiente" else None

    def _available(self, client, owner, document_id, adaptation_id=None):
        if self._pending(client, owner, document_id) or (adaptation_id and self._pending(client, owner, document_id, adaptation_id)):
            raise HistoryError(409, "ELIMINACION_PENDIENTE", "Hay una eliminación incompleta. Volvé al historial y reintentá eliminar.")

    def ensure_writable(self, owner, document_id, started):
        with self._client() as client:
            record = self._optional(client, self._deletion_key(owner, document_id), DeletionRecord)
            if record and (record.estado == "pendiente" or record.fecha >= started):
                raise HistoryError(409, "DOCUMENTO_ELIMINADO", "El documento se eliminó mientras se generaba el contenido. El resultado no se guardó en el historial.")

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

    @synchronized
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

    @synchronized
    def save(self, owner, document, result, started):
        reference = HistorialReferencia(status="error", mensaje="El resultado está disponible, pero no se confirmó su registro en el historial.")
        try:
            document.file.seek(0)
            document_id = sha256(document.file.read()).hexdigest()
            self.ensure_writable(owner, document_id, started)
            result = self.storage.guardar(document, result, scope=owner)
            if result.almacenamiento_oci.status_upload == "subido" and result.almacenamiento_oci.documento_original_subido is True:
                reference = HistorialReferencia(**self.register(owner, document, result))
        except Exception as error:
            logger.warning("No se confirmó el registro del historial: %s", type(error).__name__)
            if isinstance(error, HistoryError) and error.detail["codigo"] == "DOCUMENTO_ELIMINADO":
                reference = HistorialReferencia(status="error", mensaje=error.detail["mensaje"])
        return result.model_copy(update={"historial": reference})

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

    @synchronized
    def documents(self, owner, cursor=None):
        with self._client() as client:
            records, next_cursor = self._list(client, self._prefix(owner) + "documentos/", DocumentRecord, cursor)
            documents = [dict(r.model_dump(mode="json", exclude={"objeto_original"}),
                              eliminacion_pendiente=bool(self._pending(client, owner, r.id))) for r in records]
            # Un corte después de borrar el catálogo también debe permitir retomar.
            if not cursor:
                for key in self._keys(client, f"{self._deletions_prefix(owner)}documentos/"):
                    pending = self._record(client, key, DeletionRecord)
                    if pending.estado == "pendiente" and pending.documento and not self._optional(client, self._document_key(owner, pending.documento.id), DocumentRecord):
                        documents.append(dict(pending.documento.model_dump(mode="json", exclude={"objeto_original"}), eliminacion_pendiente=True))
        return {"documentos": documents, "siguiente": next_cursor}

    @synchronized
    def adaptations(self, owner, document_id, cursor=None):
        with self._client() as client:
            self._available(client, owner, document_id)
            self._record(client, self._document_key(owner, document_id), DocumentRecord)
            records, next_cursor = self._list(client, self._adaptation_prefix(owner, document_id), AdaptationRecord, cursor)
            if any(r.documento_id != document_id for r in records):
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "El resultado no corresponde al documento.")
            adaptations = [dict(r.model_dump(mode="json", exclude={"objeto_resultado"}),
                                eliminacion_pendiente=bool(self._pending(client, owner, document_id, r.id))) for r in records]
            if not cursor:
                for key in self._keys(client, f"{self._deletions_prefix(owner)}adaptaciones/{document_id}/"):
                    pending = self._record(client, key, DeletionRecord)
                    if pending.estado == "pendiente" and pending.adaptacion and not self._optional(client,
                            self._adaptation_key(owner, document_id, pending.adaptacion.id), AdaptationRecord):
                        adaptations.append(dict(pending.adaptacion.model_dump(mode="json", exclude={"objeto_resultado"}), eliminacion_pendiente=True))
        return {"adaptaciones": adaptations, "siguiente": next_cursor}

    @synchronized
    def original(self, owner, document_id):
        with self._client() as client:
            self._available(client, owner, document_id)
            record = self._record(client, self._document_key(owner, document_id), DocumentRecord)
            if record.id != document_id or not re.fullmatch(rf"{self._files_prefix(owner)}documentos-fuente/\d{{4}}/\d{{2}}/{document_id}-[^/]+", record.objeto_original):
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "La referencia del original no es válida.")
            data = self._get(client, record.objeto_original, settings.MAX_DOCUMENT_BYTES)
            if len(data) != record.tamano_bytes or sha256(data).hexdigest() != document_id:
                raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "El original guardado no superó la comprobación de integridad.")
        return record, data

    @synchronized
    def result(self, owner, document_id, adaptation_id):
        with self._client() as client:
            self._available(client, owner, document_id, adaptation_id)
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

    def _keys(self, client, prefix):
        keys, cursor = [], None
        while True:
            response = client.list_objects(self.storage.namespace, self.storage.bucket, prefix=prefix,
                start=cursor, limit=1000, retry_strategy=oci.retry.NoneRetryStrategy())
            keys.extend(item.name for item in response.data.objects or [])
            following = response.data.next_start_with
            if not following:
                return keys
            if following == cursor or not following.startswith(prefix):
                raise HistoryError()
            cursor = following

    def _all_adaptations(self, client, owner, document_id):
        records, cursor = [], None
        while True:
            page, cursor = self._list(client, self._adaptation_prefix(owner, document_id), AdaptationRecord, cursor)
            for record in page:
                if record.documento_id != document_id or not re.fullmatch(rf"{self._files_prefix(owner)}artefactos-generados/\d{{4}}/\d{{2}}/{document_id}-{HASH}-[a-f0-9]{{16}}\.json", record.objeto_resultado):
                    raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "La referencia del resultado no es válida.")
            records.extend(page)
            if not cursor:
                break
        # Si se borró el índice pero falló el recibo final, la interfaz aún
        # muestra ese resultado pendiente: también debe contar al confirmar.
        for key in self._keys(client, f"{self._deletions_prefix(owner)}adaptaciones/{document_id}/"):
            pending = self._record(client, key, DeletionRecord)
            record = pending.adaptacion
            if pending.estado == "pendiente" and record and not any(r.id == record.id for r in records):
                if record.documento_id != document_id or not re.fullmatch(rf"{self._files_prefix(owner)}artefactos-generados/\d{{4}}/\d{{2}}/{document_id}-{HASH}-[a-f0-9]{{16}}\.json", record.objeto_resultado):
                    raise HistoryError(502, "REGISTRO_HISTORIAL_INVALIDO", "La referencia del resultado no es válida.")
                records.append(record)
        return records

    def _version(self, document, adaptations):
        return sha256(json_bytes({"documento": document.model_dump(mode="json"),
            "adaptaciones": sorted((r.model_dump(mode="json") for r in adaptations), key=lambda r: r["id"])})).hexdigest()

    @synchronized
    def deletion_summary(self, owner, document_id):
        with self._client() as client:
            pending = self._pending(client, owner, document_id)
            if pending and pending.documento:
                return {"nombre": pending.documento.nombre, "resultados": pending.cantidad,
                        "version": pending.version, "pendiente": True}
            document = self._record(client, self._document_key(owner, document_id), DocumentRecord)
            records = self._all_adaptations(client, owner, document_id)
            return {"nombre": document.nombre, "resultados": len(records),
                    "version": self._version(document, records), "pendiente": False}

    def _delete(self, client, key):
        try:
            response = client.delete_object(self.storage.namespace, self.storage.bucket, key,
                                           retry_strategy=oci.retry.NoneRetryStrategy())
        except oci.exceptions.ServiceError as error:
            if error.status == 404:
                return
            raise
        if response.status != 204:
            raise HistoryError()

    def _save_deletion(self, client, key, record):
        self.storage._put(client, key, json_bytes(record.model_dump(mode="json")), "application/json")

    @synchronized
    def delete_document(self, owner, document_id, version):
        if not version or not re.fullmatch(HASH, version):
            raise HistoryError(428, "CONFIRMACION_REQUERIDA", "Revisá la confirmación antes de eliminar el documento.")
        with self._client() as client:
            key = self._deletion_key(owner, document_id)
            receipt = self._optional(client, key, DeletionRecord)
            if receipt and receipt.estado == "completado" and receipt.version == version:
                return {"eliminado": True}
            if receipt and receipt.estado == "pendiente":
                if receipt.version != version:
                    raise HistoryError(409, "HISTORIAL_CAMBIO", "El historial cambió. Volvé a revisar la confirmación.")
            else:
                document = self._record(client, self._document_key(owner, document_id), DocumentRecord)
                records = self._all_adaptations(client, owner, document_id)
                if self._version(document, records) != version:
                    raise HistoryError(409, "HISTORIAL_CAMBIO", "El historial cambió. Volvé a revisar la confirmación.")
                receipt = DeletionRecord(fecha=datetime.now(timezone.utc), version=version, cantidad=len(records), documento=document)
                self._save_deletion(client, key, receipt)
            # Incluye variantes anteriores del mismo hash, dentro de este navegador.
            for folder in ("documentos-fuente", "artefactos-generados"):
                prefix = f"{self._files_prefix(owner)}{folder}/"
                for object_key in self._keys(client, prefix):
                    if re.fullmatch(rf"{prefix}\d{{4}}/\d{{2}}/{document_id}-[^/]+", object_key):
                        self._delete(client, object_key)
            for prefix in (self._adaptation_prefix(owner, document_id),
                           f"{self._deletions_prefix(owner)}adaptaciones/{document_id}/"):
                for object_key in self._keys(client, prefix):
                    self._delete(client, object_key)
            self._delete(client, self._document_key(owner, document_id))
            self._save_deletion(client, key, receipt.model_copy(update={"estado": "completado", "documento": None}))
        return {"eliminado": True}

    @synchronized
    def delete_adaptation(self, owner, document_id, adaptation_id):
        with self._client() as client:
            self._available(client, owner, document_id)
            self._record(client, self._document_key(owner, document_id), DocumentRecord)
            key = self._deletion_key(owner, document_id, adaptation_id)
            receipt = self._optional(client, key, DeletionRecord)
            if receipt and receipt.estado == "completado":
                return {"eliminado": True}
            records = self._all_adaptations(client, owner, document_id)
            record = receipt.adaptacion if receipt else next((r for r in records if r.id == adaptation_id), None)
            if record is None or record.id != adaptation_id or record.documento_id != document_id:
                raise missing()
            if not re.fullmatch(rf"{self._files_prefix(owner)}artefactos-generados/\d{{4}}/\d{{2}}/{document_id}-{HASH}-[a-f0-9]{{16}}\.json", record.objeto_resultado):
                raise missing()
            if receipt is None:
                receipt = DeletionRecord(fecha=datetime.now(timezone.utc), version=sha256(adaptation_id.encode()).hexdigest(), cantidad=1, adaptacion=record)
                self._save_deletion(client, key, receipt)
            if not any(r.id != adaptation_id and r.objeto_resultado == record.objeto_resultado for r in records):
                self._delete(client, record.objeto_resultado)
            self._delete(client, self._adaptation_key(owner, document_id, adaptation_id))
            self._save_deletion(client, key, receipt.model_copy(update={"estado": "completado", "adaptacion": None}))
        return {"eliminado": True}


def get_history_storage(storage: OCIStorage | None = Depends(get_oci_storage)) -> HistoryStorage | None:
    return HistoryStorage(storage) if storage is not None and settings.HISTORY_ENABLED else None
