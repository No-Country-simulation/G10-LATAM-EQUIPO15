"""Valida Backend y cliente multipart sin proveedores externos ni red."""

from email import policy
from email.parser import BytesParser
from io import BytesIO

import httpx
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.ia_client import IAClient, get_ia_client

FORM = {"perfil_destinatario": "Senior", "formato_salida": "Flashcards", "nicho_sector": "Salud"}


def payload(formato="Flashcards"):
    items = {
        "Flashcards": [{"frente": "¿Qué es JWT?", "dorso": "Un token firmado.", "categoria_dificultad": "Intermedio"}],
        "Quiz Interactivo": [{
            "pregunta": "¿Qué aporta la firma JWT?", "opciones": ["Integridad", "Cifrado", "Compresión", "Anonimato"],
            "indice_correcto": 0, "justificacion_tecnica": "La firma verifica integridad.",
            "explicacion_distractores": "Firmar no cifra ni comprime el contenido.",
        }],
        "Resumen Ejecutivo": {
            "tldr": "JWT transporta claims firmados.", "puntos_clave": ["Integridad"],
            "impacto_negocio": "Autenticación interoperable.", "recomendaciones": ["Validar firmas"],
        },
    }[formato]
    return {
        "status": "exito", "codigo_respuesta": 200,
        "metadatos": {
            "perfil_aplicado": "Senior", "formato_generado": formato, "nicho_contexto": "Salud",
            "tiempo_estimado_estudio_minutos": 3, "conceptos_clave": ["JWT"],
        },
        "contenido_adaptado": {"titulo": "JWT", "introduccion_contextualizada": "JWT en salud.", "items": items},
        "evaluacion_calidad": {
            "anclaje_fuente_score": 0.91, "claridad_pedagogica": "Alta", "reintentos_realizados": 1,
            "observaciones": "Evaluado por IA.",
        },
        "almacenamiento_oci": {
            "bucket": "prueba", "objeto_id": "jwt.json", "status_upload": "listo_para_subida", "ruta_publica_o_par": None,
        },
    }


@pytest.fixture
def client_factory():
    clients = []

    def create(handler):
        ia_client = IAClient("http://ia-test:8001", 600, transport=httpx.MockTransport(handler))
        app.dependency_overrides[get_ia_client] = lambda: ia_client
        client = TestClient(app)
        clients.append(client)
        return client

    yield create
    for client in clients:
        client.close()
    app.dependency_overrides.clear()


def post_document(client, form=None, content=b"Documento original", filename="jwt.md"):
    return client.post("/api/v1/adaptar-contenido", data=FORM if form is None else form,
                       files={"documento_original": (filename, content)})


def test_backend_forwards_exact_bytes_and_parameters(client_factory):
    original = b"%PDF-1.7\r\n\x00\xffTexto sin extraer ni normalizar"
    calls = []

    def ia_service(request):
        calls.append(request)
        assert str(request.url) == "http://ia-test:8001/api/v1/adaptar-contenido"
        assert request.method == "POST"
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + request.headers["content-type"].encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + request.read()
        )
        parts = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
        assert parts["documento_original"].get_payload(decode=True) == original
        assert parts["documento_original"].get_filename() == "JWT en OCI.pdf"
        for field, value in FORM.items():
            assert parts[field].get_payload(decode=True).decode() == value
        assert "authorization" not in request.headers
        return httpx.Response(200, json=payload())

    response = post_document(client_factory(ia_service), content=original, filename="JWT en OCI.pdf")
    assert response.status_code == 200
    assert response.json() == payload()
    assert len(calls) == 1


@pytest.mark.parametrize("formato", ["Flashcards", "Quiz Interactivo", "Resumen Ejecutivo"])
def test_all_mvp_formats_are_preserved(client_factory, formato):
    expected = payload(formato)
    # Campos adicionales deben sobrevivir al transporte y a la validación.
    expected["document_id"] = "doc-123"
    expected["metadatos"]["origen"] = "IA"
    expected["evaluacion_calidad"]["evidencia"] = ["chunk-1"]
    client = client_factory(lambda request: httpx.Response(200, json=expected))
    response = post_document(client, form={**FORM, "formato_salida": formato})
    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize("field,value", [
    ("perfil_destinatario", "Principiante"), ("formato_salida", "Guia Paso a Paso"),
    ("formato_salida", "Mapa Mental"), ("nicho_sector", "Otro"),
    ("perfil_destinatario", None), ("formato_salida", None), ("nicho_sector", None),
])
def test_invalid_parameters_never_contact_ia(client_factory, field, value):
    def forbidden(request):
        pytest.fail("Backend no debe contactar IA ante parámetros inválidos")
    client = client_factory(forbidden)
    form = dict(FORM)
    if value is None:
        form.pop(field)
    else:
        form[field] = value
    response = post_document(client, form=form)
    assert response.status_code == 422
    assert response.json()["detail"]["codigo"] == "PARAMETROS_INVALIDOS"


def test_old_json_contract_and_missing_file_are_rejected(client_factory):
    client = client_factory(lambda request: pytest.fail("IA no debe ser llamada"))
    assert client.post("/api/v1/adaptar-contenido", json={**FORM, "documento_contenido": "texto"}).status_code == 422
    assert client.post("/api/v1/adaptar-contenido", data=FORM).status_code == 422


@pytest.mark.parametrize("filename,content,status", [
    ("archivo.docx", b"texto", 415), ("archivo.md", b"", 422), ("archivo.txt", b"123456", 413),
])
def test_file_validation_never_contacts_ia(client_factory, monkeypatch, filename, content, status):
    monkeypatch.setattr(settings, "MAX_DOCUMENT_BYTES", 5)
    client = client_factory(lambda request: pytest.fail("IA no debe ser llamada"))
    assert post_document(client, content=content, filename=filename).status_code == status


@pytest.mark.parametrize("status,code", [
    (422, "CONTEXTO_INSUFICIENTE"), (422, "DOCUMENTO_RECHAZADO"),
    (503, "IA_OCUPADA"), (503, "PROVEEDOR_NO_DISPONIBLE"), (500, "ERROR_INTERNO_IA"),
    (502, "ERROR_PROCESAMIENTO_IA"), (504, "PROVEEDOR_TIMEOUT"),
])
def test_ia_errors_keep_status_and_code_without_leaking_body(client_factory, status, code):
    client = client_factory(lambda request: httpx.Response(
        status, json={"detail": {"codigo": code, "mensaje": "private-key-and-document-content"}},
        headers={"Retry-After": "5", "X-Internal-Secret": "private-key"},
    ))
    response = post_document(client)
    assert response.status_code == status
    assert response.json()["detail"]["codigo"] == code
    assert "private-" not in response.text
    assert "x-internal-secret" not in response.headers
    if status == 503:
        assert response.headers["retry-after"] == "5"
    else:
        assert "retry-after" not in response.headers


@pytest.mark.parametrize("failure,status,code", [
    (httpx.ConnectError("private-url"), 503, "IA_NO_DISPONIBLE"),
    (httpx.ReadTimeout("private-url"), 504, "IA_TIMEOUT"),
])
def test_unavailable_ia_has_no_mock_or_automatic_retry(client_factory, failure, status, code):
    calls = []
    def unavailable(request):
        calls.append(request)
        raise failure
    client = client_factory(unavailable)
    response = post_document(client)
    assert response.status_code == status
    assert response.json()["detail"]["codigo"] == code
    assert "private-url" not in response.text
    assert len(calls) == 1
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("upstream", [
    httpx.Response(200, text="private-key not JSON"),
    httpx.Response(200, json={}),
    httpx.Response(200, json=[]),
    httpx.Response(302, headers={"Location": "https://example.com"}, json={}),
    httpx.Response(503, json={"detail": "private-key"}),
    httpx.Response(503, json={"detail": {"codigo": ["IA_OCUPADA"]}}),
    httpx.Response(503, json={"detail": {"codigo": "UNKNOWN", "mensaje": "private-key"}}),
    httpx.Response(500, json={"detail": {"codigo": "IA_OCUPADA"}}),
])
def test_invalid_ia_responses_are_rejected(client_factory, upstream):
    client = client_factory(lambda request: upstream)
    response = post_document(client)
    assert response.status_code == 502
    assert response.json()["detail"]["codigo"] == "RESPUESTA_IA_INVALIDA"
    assert "private-key" not in response.text


@pytest.mark.parametrize("field,value", [
    ("perfil_aplicado", "Junior"), ("formato_generado", "Quiz Interactivo"), ("nicho_contexto", "General"),
])
def test_response_for_other_parameters_is_rejected(client_factory, field, value):
    incorrect = payload()
    incorrect["metadatos"][field] = value
    client = client_factory(lambda request: httpx.Response(200, json=incorrect))
    assert post_document(client).status_code == 502


def test_wrong_content_shape_for_declared_format_is_rejected(client_factory):
    incorrect = payload("Resumen Ejecutivo")
    incorrect["metadatos"]["formato_generado"] = "Flashcards"
    client = client_factory(lambda request: httpx.Response(200, json=incorrect))
    assert post_document(client).status_code == 502


def test_untrusted_retry_header_is_not_forwarded(client_factory):
    client = client_factory(lambda request: httpx.Response(
        503, json={"detail": {"codigo": "IA_OCUPADA"}}, headers={"Retry-After": "private-key"},
    ))
    response = post_document(client)
    assert response.status_code == 503
    assert "retry-after" not in response.headers


def test_client_rewinds_stream_before_sending():
    stream = BytesIO(b"contenido original")
    stream.read(5)
    upload = UploadFile(stream, filename="jwt.md")
    def service(request):
        assert b"contenido original" in request.read()
        return httpx.Response(200, json=payload())
    try:
        result = IAClient("http://ia-test", 600, httpx.MockTransport(service)).adaptar(upload, "Senior", "Flashcards", "Salud")
        assert result.metadatos.perfil_aplicado.value == "Senior"
    finally:
        stream.close()


def test_swagger_exposes_file_and_canonical_choices(client_factory):
    client = client_factory(lambda request: pytest.fail("IA no debe ser llamada"))
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/api/v1/adaptar-contenido"]["post"]
    ref = operation["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    body = spec["components"]["schemas"][ref.rsplit("/", 1)[-1]]
    assert set(body["required"]) == {"documento_original", *FORM}
    assert body["properties"]["documento_original"]["format"] == "binary"
    assert spec["components"]["schemas"]["PerfilDestinatario"]["enum"] == ["Junior", "Senior", "Ejecutivo"]
