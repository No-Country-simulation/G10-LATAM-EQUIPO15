"""Pruebas sin OCI: SDK y firmas reales, transporte HTTP controlado y sin red."""

import base64
from datetime import datetime, timezone
from hashlib import md5, sha256
from io import BytesIO
import json
from urllib.parse import unquote

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import UploadFile
from fastapi.testclient import TestClient
import httpx
import oci
import pytest
# OCI incluye su propia copia de requests; el adaptador debe usar esa implementación.
from oci._vendor import requests
from oci._vendor.requests.adapters import BaseAdapter

from app.api.schemas import AdaptacionResponse
from app.core.config import settings
from app.main import app
from app.services.ia_client import IAClient, get_ia_client
from app.services.oci_service import OCIStorage, create_oci_client, get_oci_storage
from test_ia_integration import FORM, payload, post_document


@pytest.fixture(scope="module")
def signing_key():
    # Clave efímera del fixture; no pertenece a ninguna cuenta OCI.
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption()).decode()


class ControlledTransport(BaseAdapter):
    def __init__(self, statuses=(200, 200), failure=None):
        self.calls = []
        self.statuses = statuses
        self.failure = failure
        self.closed = False

    def send(self, request, **kwargs):
        body = request.body.read() if hasattr(request.body, "read") else request.body
        self.calls.append({"url": request.url, "headers": dict(request.headers), "body": body, "options": kwargs})
        if self.failure is not None:
            raise self.failure
        status = self.statuses[min(len(self.calls) - 1, len(self.statuses) - 1)]
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.status_code = status
        response.headers = {"content-type": "application/json", "opc-request-id": "fixture"}
        response._content = b'{}' if status == 200 else b'{"code":"FixtureFailure","message":"private-key-and-document-content"}'
        return response

    def close(self):
        self.closed = True


@pytest.fixture
def sdk_factory(signing_key):
    clients = []
    public_key = serialization.load_pem_private_key(signing_key.encode(), password=None).public_key()
    public_der = public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    fingerprint_hex = md5(public_der, usedforsecurity=False).hexdigest()
    fingerprint = ":".join(fingerprint_hex[i:i + 2] for i in range(0, 32, 2))
    config = {"user": "ocid1.user.oc1..fixture", "tenancy": "ocid1.tenancy.oc1..fixture",
              "fingerprint": fingerprint, "key_content": signing_key, "region": "us-ashburn-1"}

    def create(statuses=(200, 200), failure=None):
        client = oci.object_storage.ObjectStorageClient(
            config, service_endpoint="https://objectstorage.fixture.invalid",
            timeout=(5, 10), retry_strategy=oci.retry.NoneRetryStrategy(),
        )
        transport = ControlledTransport(statuses, failure)
        client.base_client.session.mount("https://", transport)
        clients.append(client)
        return client, transport

    yield create
    for client in clients:
        client.base_client.session.close()


def service(client):
    return OCIStorage("namespace-fixture", "bucket-fixture", client_factory=lambda: client,
                      clock=lambda: datetime(2026, 10, 8, tzinfo=timezone.utc))


def document(data=b"%PDF-1.7\r\n\x00\xfforiginal", filename="JWT en OCI.pdf"):
    upload = UploadFile(filename=filename, file=BytesIO(data))
    upload.file.seek(0, 2)  # Simula el stream consumido previamente por IA.
    return upload


@pytest.mark.parametrize("formato", ["Flashcards", "Quiz Interactivo", "Resumen Ejecutivo"])
def test_real_sdk_uploads_original_and_same_public_json(sdk_factory, formato):
    client, transport = sdk_factory()
    previous = AdaptacionResponse.model_validate(payload(formato))
    original = document()
    expected_bytes = original.file.getvalue()
    result = service(client).guardar(original, previous)
    public = result.model_dump(mode="json", exclude_unset=True)
    storage = public["almacenamiento_oci"]
    assert len(public) == 6
    assert storage["status_upload"] == "subido"
    assert storage["documento_original_subido"] is True
    assert storage["ruta_publica_o_par"] is None
    assert storage["bucket"] == "bucket-fixture"
    assert len(transport.calls) == 2
    assert transport.closed
    assert transport.calls[0]["body"] == expected_bytes
    assert json.loads(transport.calls[1]["body"]) == public
    assert storage["documento_original_objeto_id"] in unquote(transport.calls[0]["url"])
    assert storage["objeto_id"] in unquote(transport.calls[1]["url"])
    for call in transport.calls:
        headers = {key.lower(): value for key, value in call["headers"].items()}
        assert headers["content-length"] == str(len(call["body"]))
        assert headers["content-md5"] == base64.b64encode(md5(call["body"], usedforsecurity=False).digest()).decode()
        assert headers["authorization"].startswith("Signature ")
        assert call["options"]["timeout"] == (5, 10)
    assert previous.almacenamiento_oci.status_upload == "listo_para_subida"
    assert public["contenido_adaptado"] == payload(formato)["contenido_adaptado"]
    assert public["evaluacion_calidad"] == payload(formato)["evaluacion_calidad"]


def test_backend_ignores_provider_paths_and_sanitizes_original_filename(sdk_factory):
    client, transport = sdk_factory()
    data = payload()
    data["almacenamiento_oci"].update(objeto_id="../../provider-object.json", ruta_publica_o_par="https://private-par")
    original = document(filename=r"C:\temp\..\JWT?archivo.pdf")
    result = service(client).guardar(original, AdaptacionResponse.model_validate(data))
    storage = result.almacenamiento_oci
    assert ".." not in storage.objeto_id and "provider" not in storage.objeto_id
    assert storage.documento_original_objeto_id.endswith("-JWT_archivo.pdf")
    assert sha256(original.file.getvalue()).hexdigest() in storage.documento_original_objeto_id
    assert storage.ruta_publica_o_par is None
    assert all("private-par" not in str(call) for call in transport.calls)


def test_object_identity_reuses_equal_content_and_separates_variants(sdk_factory):
    client, transport = sdk_factory(statuses=(200,))
    storage = service(client)
    first = storage.guardar(document(), AdaptacionResponse.model_validate(payload()))
    second = storage.guardar(document(), AdaptacionResponse.model_validate(payload()))
    quiz = storage.guardar(document(), AdaptacionResponse.model_validate(payload("Quiz Interactivo")))
    changed = payload()
    changed["contenido_adaptado"]["items"][0]["dorso"] = "Otra explicación."
    revised = storage.guardar(document(), AdaptacionResponse.model_validate(changed))
    assert first.almacenamiento_oci.objeto_id == second.almacenamiento_oci.objeto_id
    assert first.almacenamiento_oci.documento_original_objeto_id == quiz.almacenamiento_oci.documento_original_objeto_id
    assert len({first.almacenamiento_oci.objeto_id, quiz.almacenamiento_oci.objeto_id, revised.almacenamiento_oci.objeto_id}) == 3
    assert len(transport.calls) == 8  # Dos PutObject por adaptación, sin Head/List ni reintentos.


@pytest.mark.parametrize("statuses,expected,confirmed,count,code", [
    ((403,), "error", False, 1, "OCI_ACCESO_DENEGADO"),
    ((401,), "error", False, 1, "OCI_ACCESO_DENEGADO"),
    ((404,), "error", False, 1, "OCI_NO_DISPONIBLE"),
    ((503,), "error", False, 1, "OCI_NO_DISPONIBLE"),
    ((200, 403), "parcial", True, 2, "OCI_ACCESO_DENEGADO"),
    ((200, 500), "parcial", True, 2, "OCI_NO_DISPONIBLE"),
    ((200, 202), "parcial", True, 2, "OCI_NO_DISPONIBLE"),
])
def test_failed_uploads_never_claim_success_or_repeat_requests(sdk_factory, caplog, statuses, expected, confirmed, count, code):
    client, transport = sdk_factory(statuses)
    previous = AdaptacionResponse.model_validate(payload())
    result = service(client).guardar(document(), previous)
    assert result.almacenamiento_oci.status_upload == expected
    assert result.almacenamiento_oci.documento_original_subido is confirmed
    assert result.almacenamiento_oci.codigo_error == code
    assert len(transport.calls) == count
    assert transport.closed
    assert result.contenido_adaptado == previous.contenido_adaptado
    assert "private-key-and-document-content" not in result.model_dump_json() + caplog.text


def test_read_timeout_does_not_confirm_upload_or_trigger_an_automatic_retry(sdk_factory, caplog):
    client, transport = sdk_factory(failure=requests.exceptions.ReadTimeout("private-url"))
    result = service(client).guardar(document(), AdaptacionResponse.model_validate(payload()))
    assert result.almacenamiento_oci.status_upload == "error"
    assert result.almacenamiento_oci.documento_original_subido is False
    assert len(transport.calls) == 1
    assert "private-url" not in result.model_dump_json() + caplog.text


def test_invalid_local_configuration_preserves_result_without_leaking_paths(caplog):
    def unavailable():
        raise FileNotFoundError("private-key-path")
    storage = OCIStorage("fixture", "bucket", client_factory=unavailable)
    previous = AdaptacionResponse.model_validate(payload())
    result = storage.guardar(document(), previous)
    assert result.almacenamiento_oci.status_upload == "error"
    assert result.almacenamiento_oci.codigo_error == "OCI_NO_CONFIGURADO"
    assert result.contenido_adaptado == previous.contenido_adaptado
    assert "private-key-path" not in result.model_dump_json() + caplog.text


def test_disabled_storage_never_initializes_sdk_or_reads_private_config(monkeypatch):
    monkeypatch.setattr(settings, "OCI_STORAGE_ENABLED", False)
    monkeypatch.setattr(oci.config, "from_file", lambda *args: pytest.fail("No leer credenciales con OCI desactivado"))
    assert get_oci_storage() is None


def test_api_key_configuration_uses_private_profile_and_region_override(monkeypatch, signing_key):
    observed = []
    def read_config(file, profile):
        observed.append((file, profile))
        return {"user": "ocid1.user.oc1..fixture", "tenancy": "ocid1.tenancy.oc1..fixture", "fingerprint": ":".join(["aa"] * 16),
                "key_content": signing_key, "region": "us-ashburn-1"}
    monkeypatch.setattr(oci.config, "from_file", read_config)
    monkeypatch.setattr(settings, "OCI_AUTH_MODE", "api_key")
    monkeypatch.setattr(settings, "OCI_CONFIG_FILE", "/run/secrets/oci/config")
    monkeypatch.setattr(settings, "OCI_CONFIG_PROFILE", "EQUIPO")
    monkeypatch.setattr(settings, "OCI_REGION", "us-phoenix-1")
    client = create_oci_client()
    assert observed == [("/run/secrets/oci/config", "EQUIPO")]
    assert "us-phoenix-1" in client.base_client.endpoint
    client.base_client.session.close()


@pytest.fixture
def endpoint_factory(sdk_factory, monkeypatch):
    # Estas regresiones verifican el contrato dual original; el catálogo se prueba aparte.
    monkeypatch.setattr(settings, "HISTORY_ENABLED", False)
    clients = []
    def create(handler=None, statuses=(200, 200)):
        sdk, transport = sdk_factory(statuses)
        app.dependency_overrides[get_oci_storage] = lambda: service(sdk)
        ia = IAClient("http://ia-test:8001", 600, transport=httpx.MockTransport(
            handler or (lambda request: httpx.Response(200, json=payload())),
        ))
        app.dependency_overrides[get_ia_client] = lambda: ia
        client = TestClient(app)
        clients.append(client)
        return client, transport
    yield create
    for client in clients:
        client.close()
    app.dependency_overrides.clear()


def test_endpoint_stores_bytes_after_ia_consumes_original_stream(endpoint_factory):
    client, transport = endpoint_factory()
    original = b"\x00\xffDocumento binario sin normalizar"
    response = post_document(client, content=original, filename="JWT.pdf")
    assert response.status_code == 200
    assert transport.calls[0]["body"] == original
    assert json.loads(transport.calls[1]["body"]) == response.json()
    assert response.json()["almacenamiento_oci"]["status_upload"] == "subido"


@pytest.mark.parametrize("statuses,state", [((403,), "error"), ((200, 503), "parcial")])
def test_endpoint_preserves_valid_adaptation_when_storage_fails(endpoint_factory, statuses, state):
    client, transport = endpoint_factory(statuses=statuses)
    response = post_document(client)
    assert response.status_code == 200 and response.json()["status"] == "exito"
    assert response.json()["almacenamiento_oci"]["status_upload"] == state
    assert response.json()["contenido_adaptado"] == payload()["contenido_adaptado"]


@pytest.mark.parametrize("failure", ["invalid_input", "invalid_ia", "rejected_ia"])
def test_invalid_or_rejected_requests_never_write_to_storage(endpoint_factory, failure):
    handler = {
        "invalid_input": lambda request: pytest.fail("No contactar IA"),
        "invalid_ia": lambda request: httpx.Response(200, json={}),
        "rejected_ia": lambda request: httpx.Response(422, json={"detail": {"codigo": "CONTEXTO_INSUFICIENTE"}}),
    }[failure]
    client, transport = endpoint_factory(handler)
    response = post_document(client, form={**FORM, "perfil_destinatario": "invalido"} if failure == "invalid_input" else None)
    assert response.status_code in {422, 502}
    assert transport.calls == []


@pytest.mark.parametrize("claimed", ["subido", "parcial", "error"])
def test_ia_cannot_claim_backend_storage_results(endpoint_factory, claimed):
    data = payload()
    data["almacenamiento_oci"]["status_upload"] = claimed
    client, transport = endpoint_factory(lambda request: httpx.Response(200, json=data))
    response = post_document(client)
    assert response.status_code == 502
    assert response.json()["detail"]["codigo"] == "RESPUESTA_IA_INVALIDA"
    assert transport.calls == []


@pytest.mark.parametrize("reference", [None, {"status":"disponible", "documento_id":"identificador-propuesto-por-ia"}])
def test_ia_no_puede_proponer_un_historial_confirmado(endpoint_factory, reference):
    data = payload()
    data["historial"] = reference
    client, transport = endpoint_factory(lambda request: httpx.Response(200, json=data))
    response = post_document(client)
    assert response.status_code == 502
    assert transport.calls == []
