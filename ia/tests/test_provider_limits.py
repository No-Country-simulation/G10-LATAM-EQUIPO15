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
from dataia.vectorstore import service as vectorstore
from dataia.vectorstore.client import get_embeddings_model
from src.ai.agents.critico import nodo_critico


@pytest.fixture(autouse=True)
def configured(monkeypatch):
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
        nodo_critico({"documento_contenido":"JWT autentica mediante tokens.", "borrador_contenido":{"items":[]}})
    assert error.value is failure
