"""Regresiones de opciones efectivas del SDK y conservación de fallos."""

import logging
from unittest.mock import Mock

import httpx
import pytest
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import BaseModel

from dataia.common import providers
from dataia.common.models import ChunkingResult, IngestionResult
from dataia.chunking import service as chunking
from dataia.chunking import structural_splitter
from dataia.ingestion import enrichment
from dataia.vectorstore import service as vectorstore
from dataia.vectorstore.client import get_embeddings_model
from src.ai.agents.critico import nodo_critico


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.delenv("DATAIA_GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key_without_network")
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_without_network")
    monkeypatch.setenv("IA_STRICT_PROVIDERS", "1")
    monkeypatch.setenv("IA_PROVIDER_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("IA_PROVIDER_MAX_RETRIES", "1")


def test_structured_generation_sends_timeout_and_total_attempts_to_sdk(monkeypatch):
    class Output(BaseModel):
        value: str

    llm = providers.create_gemini_llm()
    response = types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=[types.Part(text='{"value":"ok"}')]),
        finish_reason="STOP",
    )])
    invoke = Mock(return_value=response)
    monkeypatch.setattr(llm.client.models, "generate_content", invoke)
    try:
        result = llm.with_structured_output(Output).invoke("Extraer el valor.")
        assert result.value == "ok"
        options = invoke.call_args.kwargs["config"].http_options
        assert options.timeout == 12500
        assert options.retry_options.attempts == 2
    finally:
        llm.client.close()


def test_embedding_query_uses_bounded_sdk_client(monkeypatch):
    embeddings = get_embeddings_model()
    invoke = Mock(return_value=types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=[0.25, 0.75])],
    ))
    monkeypatch.setattr(embeddings.client.models, "embed_content", invoke)
    try:
        assert embeddings.embed_query("JWT") == [0.25, 0.75]
        options = embeddings.client._api_client._http_options
        assert options.timeout == 12500
        assert options.retry_options.attempts == 2
    finally:
        embeddings.client.close()


@pytest.mark.parametrize("operation,stage,payload", [
    ("document", "ENRIQUECIMIENTO_DOCUMENTO", '{"document_id":"doc","conceptos_clave":["JWT"]}'),
    ("batch", "ENRIQUECIMIENTO_LOTE", '{"fragmentos":[{"indice":0,"tipo_contenido":"definicion","nivel_dificultad":2,"concepto_principal":"JWT"}]}'),
])
def test_dataia_enrichment_keeps_limits_and_own_key(monkeypatch, tmp_path, caplog, operation, stage, payload):
    monkeypatch.setenv("DATAIA_GOOGLE_API_KEY", "test_dataia_key_without_network")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "")  # esta prueba verifica el modelo principal
    monkeypatch.setattr(enrichment, "CACHE_DIR", str(tmp_path / "document"))
    monkeypatch.setattr(structural_splitter, "CACHE_DIR", str(tmp_path / "chunks"))
    models = []
    calls = []

    def bounded_factory(*args, **kwargs):
        llm = providers.create_gemini_llm(*args, **kwargs)
        models.append(llm)
        response = types.GenerateContentResponse(candidates=[types.Candidate(
            content=types.Content(role="model", parts=[types.Part(text=payload)]), finish_reason="STOP",
        )])
        invoke = Mock(return_value=response)
        calls.append(invoke)
        monkeypatch.setattr(llm.client.models, "generate_content", invoke)
        return llm

    monkeypatch.setattr(enrichment, "create_gemini_llm", bounded_factory)
    monkeypatch.setattr(structural_splitter, "create_gemini_llm", bounded_factory)
    try:
        with caplog.at_level(logging.INFO):
            if operation == "document":
                enrichment.enrich_document_metadata("doc", "JWT técnico")
            else:
                structural_splitter.enrich_chunks_metadata(["JWT técnico"])
        assert len(models) == 1
        assert models[0].google_api_key.get_secret_value() == "test_dataia_key_without_network"
        options = calls[0].call_args.kwargs["config"].http_options
        assert options.timeout == 12500
        assert options.retry_options.attempts == 2
        assert f"etapa={stage} estado=fin" in caplog.text
        assert "test_dataia_key_without_network" not in caplog.text
    finally:
        for llm in models:
            llm.client.close()


def test_embedding_own_key_keeps_bounded_sdk_client(monkeypatch):
    monkeypatch.setenv("DATAIA_GOOGLE_API_KEY", "test_dataia_key_without_network")
    embeddings = get_embeddings_model()
    try:
        assert embeddings.google_api_key.get_secret_value() == "test_dataia_key_without_network"
        options = embeddings.client._api_client._http_options
        assert options.timeout == 12500
        assert options.retry_options.attempts == 2
    finally:
        embeddings.client.close()


@pytest.mark.parametrize("model,expected", [("gemini-3.1-flash-lite", None), ("gemini-2.5-flash", 0.3)])
def test_gemini_3_keeps_recommended_default_temperature(monkeypatch, model, expected):
    monkeypatch.setenv("GEMINI_MODEL", model)
    llm = providers.create_gemini_llm(0.3)
    try:
        assert llm.temperature == expected
    finally:
        llm.client.close()


@pytest.mark.parametrize("name,value", [
    ("IA_PROVIDER_TIMEOUT_SECONDS", "0"), ("IA_PROVIDER_TIMEOUT_SECONDS", "nan"),
    ("IA_PROVIDER_MAX_RETRIES", "-1"), ("IA_PROVIDER_MAX_RETRIES", "3"),
])
def test_invalid_provider_limits_are_rejected(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        providers.provider_limits()


@pytest.mark.parametrize("failure,category,code", [
    (ClientError(429, {"error": {"message": "private-key private-document"}}), "cuota", 429),
    (ServerError(503, {"error": {"message": "private-key private-document"}}), "indisponibilidad", 503),
    (httpx.ReadTimeout("private-key private-document"), "timeout", None),
])
def test_provider_logs_original_code_and_stage_without_raw_error(caplog, failure, category, code):
    wrapped = RuntimeError("private-wrapper")
    wrapped.__cause__ = failure
    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError):
        with providers.provider_call("ENRIQUECIMIENTO_FRAGMENTO"):
            raise wrapped
    assert "etapa=ENRIQUECIMIENTO_FRAGMENTO" in caplog.text
    assert f"categoria={category}" in caplog.text
    assert f"codigo={code}" in caplog.text
    assert "private-" not in caplog.text


@pytest.mark.parametrize("service,operation,input_value", [
    (chunking, "perform_structural_chunking", IngestionResult(document_id="doc", content=[
        {"text":"JWT técnico", "metadata":{"document_id":"doc", "name":"jwt", "doc_type":"md"}},
    ])),
    (vectorstore, "insert_chunks", ChunkingResult(document_id="doc", chunks=[
        {"text":"JWT técnico", "metadata":{"document_id":"doc", "chunk_id":"chunk", "name":"jwt", "doc_type":"md"}},
    ])),
])
def test_strict_data_services_preserve_provider_cause(monkeypatch, service, operation, input_value):
    failure = ClientError(429, {"error":{"message":"private-key"}})
    # Los embeddings son opcionales: solo con ellos activados se llama al proveedor al indexar.
    monkeypatch.setenv("DATAIA_EMBEDDINGS_ENABLED", "true")
    monkeypatch.setattr(service, operation, Mock(side_effect=failure))
    execute = service.process_chunks if service is chunking else service.process_vectorstore
    with pytest.raises(ClientError) as error:
        execute(input_value)
    assert error.value is failure
    monkeypatch.delenv("IA_STRICT_PROVIDERS")
    assert execute(input_value).status == "rechazado"


def test_strict_critic_does_not_convert_provider_timeout_into_low_fidelity(monkeypatch):
    failure = httpx.ReadTimeout("private-key")
    llm = Mock()
    llm.with_structured_output.return_value.invoke.side_effect = failure
    monkeypatch.setattr("src.ai.config.obtener_llm_adaptacion", Mock(return_value=llm))
    with pytest.raises(httpx.ReadTimeout) as error:
        nodo_critico({
            "documento_contenido": "JWT autentica mediante tokens.",
            "borrador_contenido": {"items": [{"frente": "JWT", "dorso": "Un token."}]},
        })
    assert error.value is failure


def _respuesta(texto):
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(role="model", parts=[types.Part(text=texto)]), finish_reason="STOP",
    )])


def test_modelo_gemini_sobrecargado_usa_el_respaldo(monkeypatch):
    # Gemini devolvió 503 (sobrecarga) en las pruebas reales; un modelo con cuota propia lo cubre.
    class Output(BaseModel):
        value: str

    monkeypatch.setenv("IA_PROVIDER_MAX_RETRIES", "0")
    principal = providers.create_gemini_llm()
    respaldo = providers.create_gemini_llm(model="gemini-3.1-flash-lite")
    sobrecarga = Mock(side_effect=ServerError(503, {"error": {"code": 503, "message": "overloaded"}}))
    monkeypatch.setattr(principal.client.models, "generate_content", sobrecarga)
    monkeypatch.setattr(respaldo.client.models, "generate_content", Mock(return_value=_respuesta('{"value":"respaldo"}')))
    try:
        cadena = providers.with_fallback_chain(principal, [respaldo])
        assert cadena.with_structured_output(Output).invoke("x").value == "respaldo"
        assert sobrecarga.called
        assert respaldo.model.removeprefix("models/") == "gemini-3.1-flash-lite"
    finally:
        principal.client.close()
        respaldo.client.close()


def test_modelos_de_respaldo_excluyen_al_principal(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-a")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "gemini-a, gemini-b ,,gemini-c")
    assert providers.gemini_fallback_models() == ["gemini-b", "gemini-c"]
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "")
    assert providers.gemini_fallback_models() == []


@pytest.mark.parametrize("critico,modelos_groq", [
    (False, ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]),
    (True, ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]),
])
def test_ai_core_encadena_gemini_y_groq(monkeypatch, critico, modelos_groq):
    from src.ai import config
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key_without_network")
    monkeypatch.delenv("GEMINI_FALLBACK_MODELS", raising=False)
    llm = config.obtener_llm_critico() if critico else config.obtener_llm_adaptacion()
    modelos = [getattr(m, "model", None) or getattr(m, "model_name", None) for m in llm.fallbacks]
    # Respaldo Gemini con cuota propia y, al final, Groq con el orden de modelos de cada rol
    # (el límite gratuito de Groq es de 8.000 tokens por minuto por modelo).
    assert [str(m).removeprefix("models/") for m in modelos] == ["gemini-3.1-flash-lite", *modelos_groq]


def test_groq_usa_esquema_json_para_salida_estructurada(monkeypatch):
    # Por llamada a herramientas fallaba con prompts largos ('tool_use_failed').
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key_without_network")

    class Output(BaseModel):
        value: str

    estructurado = providers.create_groq_llm(0.0, "openai/gpt-oss-120b").with_structured_output(Output)
    formato = estructurado.first.kwargs.get("response_format") or {}
    assert formato.get("type") == "json_schema"


def test_ai_core_sin_clave_de_groq_solo_usa_gemini(monkeypatch):
    from src.ai import config
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    llm = config.obtener_llm_adaptacion()
    assert [m.model.removeprefix("models/") for m in llm.fallbacks] == ["gemini-3.1-flash-lite"]


def test_groq_gpt_oss_limita_razonamiento_y_salida(monkeypatch):
    # Sin esto, gpt-oss-20b agotaba la salida razonando y pedía más de los 8.000 tokens por minuto.
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key_without_network")
    llm = providers.create_groq_llm(0.0, "openai/gpt-oss-20b")
    assert llm.reasoning_effort == "low"
    assert llm.max_tokens == 2500
    assert getattr(providers.create_groq_llm(0.0, "qwen/qwen3.8-27b"), "reasoning_effort", None) is None
