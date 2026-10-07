"""Pruebas HTTP y del adaptador, sin red ni credenciales reales."""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from google.genai.errors import ClientError, ServerError

from ia_http import main, runner
from src.ai.agents import creador
from src.ai.schemas import AdaptacionContenidoResponse, NichoSectorEnum, PerfilDestinatarioEnum

FORM = {"perfil_destinatario": "Junior", "formato_salida": "Flashcards", "nicho_sector": "General"}


@pytest.fixture
def result():
    return AdaptacionContenidoResponse.model_validate({
        "status": "exito",
        "metadatos": {
            "perfil_aplicado": "Junior", "formato_generado": "Flashcards",
            "tiempo_estimado_estudio_minutos": 3, "conceptos_clave": ["JWT"], "nicho_contexto": "General",
        },
        "contenido_adaptado": {
            "titulo": "JWT", "introduccion_contextualizada": "Introducción técnica.",
            "items": [{"frente": "¿Qué es JWT?", "dorso": "Un formato de token firmado."}],
        },
        "evaluacion_calidad": {"anclaje_fuente_score": 0.9},
        "almacenamiento_oci": {"objeto_id": "jwt.json", "status_upload": "listo_para_subida"},
    })


@pytest.fixture
def configured(monkeypatch):
    # La suite anterior coloca claves ficticias al importarse. Estas pruebas
    # fijan explícitamente su entorno y reemplazan la llamada al pipeline.
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key_without_network")
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_without_network")
    monkeypatch.setenv("IA_STRICT_PROVIDERS", "1")


@pytest.fixture
def http_client(result):
    captured = []

    def fake_pipeline(**kwargs):
        path = Path(kwargs["ruta_archivo"])
        captured.append({**kwargs, "bytes": path.read_bytes(), "path": path})
        return result

    main.app.dependency_overrides[runner.get_pipeline_runner] = lambda: fake_pipeline
    try:
        with TestClient(main.app) as client:
            yield client, captured
    finally:
        main.app.dependency_overrides.clear()


@pytest.mark.parametrize("extension", ["pdf", "md", "markdown", "TXT"])
def test_original_file_reaches_pipeline_and_is_deleted(http_client, extension):
    client, captured = http_client
    original = b"\x00Texto original\r\n\tcon bytes intactos\xff"
    response = client.post("/api/v1/adaptar-contenido", data=FORM,
                           files={"documento_original": (f"JWT en OCI.{extension}", original)})
    assert response.status_code == 200
    assert response.json()["evaluacion_calidad"]["anclaje_fuente_score"] == 0.9
    assert response.json()["almacenamiento_oci"]["status_upload"] == "listo_para_subida"
    call = captured[0]
    assert call["bytes"] == original
    assert call["documento_titulo"] == "JWT en OCI"
    assert (call["perfil"], call["formato"], call["nicho"]) == ("Junior", "Flashcards", "General")
    assert not call["path"].exists()
    assert not call["path"].parent.exists()


def test_filename_cannot_choose_filesystem_path(http_client):
    client, captured = http_client
    response = client.post("/api/v1/adaptar-contenido", data=FORM,
                           files={"documento_original": (r"..\..\jwt.md", b"texto")})
    assert response.status_code == 200
    assert captured[0]["path"].name == "documento.md"
    assert captured[0]["documento_titulo"] == "jwt"


@pytest.mark.parametrize("field,value", [
    ("perfil_destinatario", "Principiante"), ("formato_salida", "Guia Paso a Paso"),
    ("nicho_sector", "Otro"), ("perfil_destinatario", None),
    ("formato_salida", None), ("nicho_sector", None),
])
def test_invalid_parameters_do_not_invoke_pipeline(http_client, field, value):
    client, captured = http_client
    form = dict(FORM)
    if value is None:
        form.pop(field)
    else:
        form[field] = value
    response = client.post("/api/v1/adaptar-contenido", data=form,
                           files={"documento_original": ("jwt.md", b"texto")})
    assert response.status_code == 422
    assert response.json()["detail"]["codigo"] == "PARAMETROS_INVALIDOS"
    assert not captured


def test_json_and_missing_file_are_rejected(http_client):
    client, captured = http_client
    assert client.post("/api/v1/adaptar-contenido", json=FORM).status_code == 422
    assert client.post("/api/v1/adaptar-contenido", data=FORM).status_code == 422
    assert not captured


@pytest.mark.parametrize("filename,content,status,code", [
    ("documento.docx", b"texto", 415, "FORMATO_NO_SOPORTADO"),
    ("documento.md", b"", 422, "DOCUMENTO_VACIO"),
])
def test_invalid_document_is_rejected(http_client, filename, content, status, code):
    client, captured = http_client
    response = client.post("/api/v1/adaptar-contenido", data=FORM,
                           files={"documento_original": (filename, content)})
    assert response.status_code == status
    assert response.json()["detail"]["codigo"] == code
    assert not captured


def test_document_size_limit(http_client, monkeypatch):
    client, captured = http_client
    monkeypatch.setattr(main, "MAX_DOCUMENT_BYTES", 4)
    response = client.post("/api/v1/adaptar-contenido", data=FORM,
                           files={"documento_original": ("jwt.md", b"12345")})
    assert response.status_code == 413
    assert not captured


def test_size_limit_also_applies_without_size_metadata(monkeypatch):
    monkeypatch.setattr(main, "MAX_DOCUMENT_BYTES", 4)
    upload = UploadFile(BytesIO(b"12345"), filename="jwt.md")
    try:
        with pytest.raises(HTTPException) as error:
            main.adaptar_contenido(upload, PerfilDestinatarioEnum.JUNIOR,
                                  "Flashcards", NichoSectorEnum.GENERAL, Mock())
        assert error.value.status_code == 413
        # El lock se libera aun si la copia falla.
        assert main.pipeline_lock.acquire(blocking=False)
        main.pipeline_lock.release()
    finally:
        upload.file.close()


def test_busy_pipeline_does_not_block_health(http_client):
    client, captured = http_client
    assert main.pipeline_lock.acquire(blocking=False)
    try:
        response = client.post("/api/v1/adaptar-contenido", data=FORM,
                               files={"documento_original": ("jwt.md", b"texto")})
        assert response.status_code == 503
        assert response.json()["detail"]["codigo"] == "IA_OCUPADA"
        assert response.headers["retry-after"] == "5"
        assert client.get("/health").json() == {"status": "healthy", "service": "ia"}
        assert not captured
    finally:
        main.pipeline_lock.release()


def test_pipeline_rejection_cleans_file_and_next_request_can_run(http_client):
    client, captured = http_client
    paths = []

    def rejecting_pipeline(**kwargs):
        paths.append(Path(kwargs["ruta_archivo"]))
        raise runner.PipelineServiceError(422, "CONTEXTO_INSUFICIENTE", "Contenido rechazado por IA.")

    main.app.dependency_overrides[runner.get_pipeline_runner] = lambda: rejecting_pipeline
    for _ in range(2):
        response = client.post("/api/v1/adaptar-contenido", data=FORM,
                               files={"documento_original": ("jwt.md", b"texto")})
        assert response.status_code == 422
    assert all(not path.parent.exists() for path in paths)
    assert len(paths) == 2


def test_invalid_pipeline_response_is_not_reported_as_success(http_client):
    client, _ = http_client
    main.app.dependency_overrides[runner.get_pipeline_runner] = lambda: lambda **kwargs: {}
    response = client.post("/api/v1/adaptar-contenido", data=FORM,
                           files={"documento_original": ("jwt.md", b"texto")})
    assert response.status_code == 502
    assert response.json()["detail"]["codigo"] == "RESPUESTA_IA_INVALIDA"


def test_openapi_exposes_multipart_and_current_response(http_client):
    client, _ = http_client
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    endpoint = spec["paths"]["/api/v1/adaptar-contenido"]["post"]
    schema_ref = endpoint["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    schema = spec["components"]["schemas"][schema_ref.rsplit("/", 1)[-1]]
    assert set(schema["required"]) == {"documento_original", *FORM}
    assert schema["properties"]["documento_original"]["format"] == "binary"
    assert set(schema["properties"]["formato_salida"]["enum"]) == {
        "Flashcards", "Quiz Interactivo", "Resumen Ejecutivo",
    }


def test_adapter_calls_existing_pipeline(configured, monkeypatch, result):
    invoke = Mock(return_value=result)
    monkeypatch.setattr(runner, "ejecutar_pipeline_adaptacion", invoke)
    assert runner.run_pipeline(ruta_archivo="/tmp/documento.md", perfil="Junior") == result
    invoke.assert_called_once_with(ruta_archivo="/tmp/documento.md", perfil="Junior")


@pytest.mark.parametrize("missing", ["GOOGLE_API_KEY", "GEMINI_API_KEY", "IA_STRICT_PROVIDERS"])
def test_service_requires_credentials_and_strict_mode(configured, monkeypatch, missing):
    monkeypatch.delenv(missing)
    invoke = Mock()
    monkeypatch.setattr(runner, "ejecutar_pipeline_adaptacion", invoke)
    with pytest.raises(runner.PipelineServiceError) as error:
        runner.run_pipeline(ruta_archivo="/tmp/documento.md")
    assert (error.value.status_code, error.value.codigo) == (503, "IA_NO_CONFIGURADA")
    invoke.assert_not_called()


@pytest.mark.parametrize("failure,status,code", [
    (ValueError("Contexto Insuficiente (Error 422): private-source"), 422, "CONTEXTO_INSUFICIENTE"),
    (ValueError("Error de Ingestión: private-path"), 422, "DOCUMENTO_RECHAZADO"),
    (ValueError("Error de Chunking: private-key"), 502, "ERROR_PROCESAMIENTO_IA"),
    (ValueError("Error de VectorStore: private-key"), 502, "ERROR_PROCESAMIENTO_IA"),
    (RuntimeError("private-key"), 500, "ERROR_INTERNO_IA"),
    (ValueError("private-key"), 500, "ERROR_INTERNO_IA"),
    (httpx.ConnectError("private-key"), 503, "PROVEEDOR_NO_DISPONIBLE"),
    (httpx.ReadTimeout("private-key"), 504, "PROVEEDOR_TIMEOUT"),
    (ClientError(429, {"error": {"code": 429, "message": "private-key"}}), 503, "PROVEEDOR_NO_DISPONIBLE"),
    (ClientError(404, {"error": {"code": 404, "message": "private-key"}}), 502, "ERROR_PROVEEDOR"),
    (ServerError(503, {"error": {"code": 503, "message": "private-key"}}), 503, "PROVEEDOR_NO_DISPONIBLE"),
])
def test_pipeline_failures_have_safe_http_mapping(configured, monkeypatch, failure, status, code, caplog):
    monkeypatch.setattr(runner, "ejecutar_pipeline_adaptacion", Mock(side_effect=failure))
    with pytest.raises(runner.PipelineServiceError) as error:
        runner.run_pipeline(ruta_archivo="/tmp/documento.md")
    assert (error.value.status_code, error.value.codigo) == (status, code)
    assert "private-" not in error.value.mensaje
    assert "private-" not in caplog.text


def test_wrapped_provider_failure_is_recognized(configured, monkeypatch):
    original = ClientError(429, {"error": {"code": 429, "message": "private-key"}})
    wrapped = RuntimeError("Provider wrapper")
    wrapped.__cause__ = original
    monkeypatch.setattr(runner, "ejecutar_pipeline_adaptacion", Mock(side_effect=wrapped))
    with pytest.raises(runner.PipelineServiceError) as error:
        runner.run_pipeline()
    assert error.value.status_code == 503


def test_adapter_rejects_invalid_output(configured, monkeypatch):
    monkeypatch.setattr(runner, "ejecutar_pipeline_adaptacion", Mock(return_value={}))
    with pytest.raises(runner.PipelineServiceError) as error:
        runner.run_pipeline()
    assert (error.value.status_code, error.value.codigo) == (502, "RESPUESTA_IA_INVALIDA")


def test_creator_strict_mode_propagates_error(configured, monkeypatch):
    failure = RuntimeError("Proveedor no disponible")
    monkeypatch.setattr(creador, "obtener_llm_adaptacion", Mock(side_effect=failure))
    fallback = Mock()
    monkeypatch.setattr(creador, "_generar_borrador_fallback", fallback)
    with pytest.raises(RuntimeError, match="Proveedor no disponible"):
        creador.nodo_creador({"documento_titulo": "JWT"})
    fallback.assert_not_called()


def test_creator_keeps_legacy_fallback_outside_strict_mode(monkeypatch):
    monkeypatch.delenv("IA_STRICT_PROVIDERS", raising=False)
    monkeypatch.setattr(creador, "obtener_llm_adaptacion", Mock(side_effect=RuntimeError()))
    fallback = Mock(return_value={"titulo": "Borrador de prueba"})
    monkeypatch.setattr(creador, "_generar_borrador_fallback", fallback)
    assert creador.nodo_creador({"documento_titulo": "JWT"})["borrador_contenido"] == {"titulo": "Borrador de prueba"}
    fallback.assert_called_once()
