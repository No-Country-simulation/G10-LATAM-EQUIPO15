"""El enriquecimiento de documentos grandes envía una muestra, no el texto completo."""

from types import SimpleNamespace

from dataia.ingestion import enrichment


def test_texto_breve_se_envia_completo():
    assert enrichment._muestra_representativa("abc " * 100, max_chars=1000) == "abc " * 100


def test_texto_grande_se_muestrea_de_principio_a_fin():
    texto = "".join(f"<{i:05d}>" for i in range(20000))  # 140.000 caracteres
    muestra = enrichment._muestra_representativa(texto, max_chars=7000, ventanas=7)
    assert len(muestra) <= 7000 + 7 * len(enrichment.SEPARADOR_MUESTRA)
    assert muestra.startswith("<00000>")
    assert muestra.rstrip().endswith("<19999>")
    assert muestra.count(enrichment.SEPARADOR_MUESTRA) == 6
    # También cubre el medio del documento, no solo el inicio.
    assert any(f"<{i:05d}>" in muestra for i in range(9000, 11000))


def test_enriquecimiento_no_envia_un_documento_grande_en_una_llamada(monkeypatch, tmp_path):
    # Un libro de ~450.000 tokens en una sola llamada devolvió 429 (límite de tokens por minuto).
    prompts = []

    def invoke(prompt):
        prompts.append(prompt)
        return enrichment.DocumentPedagogicalMetadata(document_id="x", conceptos_clave=["Java"])

    llm = SimpleNamespace(with_structured_output=lambda _schema: SimpleNamespace(invoke=invoke))
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "")  # el LLM simulado no admite respaldos
    monkeypatch.setattr(enrichment, "create_gemini_llm", lambda **_kwargs: llm)
    monkeypatch.setattr(enrichment, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(enrichment, "MAX_CHARS", 10000)
    resultado = enrichment.enrich_document_metadata("doc-grande", "palabra " * 200000)
    assert resultado.conceptos_clave == ["Java"]
    assert len(prompts[0]) < 12000
