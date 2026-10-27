"""Pruebas locales de Data/IA: no usan red ni proveedores LLM."""

import pymupdf
import pytest
import re
from pathlib import Path

from dataia.chunking import structural_splitter
from dataia.chunking.structural_splitter import ChunkPedagogicalInfo, StructuralSplitter, perform_structural_chunking
from dataia.common.models import Chunk, ChunkMetadata, DocumentMetadata, ExtractedContent
from dataia.ingestion import enrichment, service as ingestion
from dataia.ingestion.normalizer import normalize_text
from dataia.vectorstore import client


INFO = ChunkPedagogicalInfo(tipo_contenido="definicion", nivel_dificultad=2, concepto_principal="JWT")
TECH_TEXT = "La arquitectura del sistema usa una API con token JWT para la seguridad del servidor en la nube. "


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.delenv("IA_STRICT_PROVIDERS", raising=False)
    monkeypatch.setattr(structural_splitter, "CACHE_DIR", str(tmp_path / "chunk_cache"))
    monkeypatch.setattr(client, "DOCUMENTS_DIRECTORY", str(tmp_path / "documents"))
    monkeypatch.setattr(ingestion, "EXTRACTION_CACHE_DIR", str(tmp_path / "extraction"))
    monkeypatch.setattr(enrichment, "enrich_document_metadata", lambda doc_id, _text: enrichment.DocumentPedagogicalMetadata(document_id=doc_id))


def content(text, page=None):
    return ExtractedContent(text=text, metadata=DocumentMetadata(document_id="doc-x", name="a.md", doc_type="md", page=page))


def test_clave_propia_de_dataia(monkeypatch):
    from dataia.common.credentials import get_google_api_key

    monkeypatch.setenv("GOOGLE_API_KEY", "clave-ai-core")
    monkeypatch.setenv("DATAIA_GOOGLE_API_KEY", "")
    assert get_google_api_key() == "clave-ai-core"
    monkeypatch.setenv("DATAIA_GOOGLE_API_KEY", "clave-dataia")
    assert get_google_api_key() == "clave-dataia"
    embeddings = client.get_embeddings_model()
    try:
        assert embeddings.google_api_key.get_secret_value() == "clave-dataia"
    finally:
        embeddings.client.close()


def test_normalizer_preserva_indentacion_y_codigo():
    text = "Lista:\n- uno\n    - anidado   con   espacios\n```python\ndef f():\n    return  1\n```"
    result = normalize_text(text)
    assert "    - anidado con espacios" in result
    assert "    return  1" in result


def test_titulo_dentro_de_codigo_no_es_seccion():
    text = (
        "# Instalación\n\nPaso inicial.\n\n```bash\n# comentario de shell\necho hola\n```\n\n"
        + "Texto posterior de la instalación. " * 400
    )
    pieces = StructuralSplitter().split_with_sections(text)
    assert len(pieces) > 1
    assert {piece.section for piece in pieces} == {"Instalación"}
    assert all(piece.text.startswith("# Instalación") for piece in pieces)


def test_documento_corto_genera_un_fragmento_por_seccion():
    # Antes un documento corto quedaba en un único fragmento y toda cita era F1.
    text = "# Título\n\n## Bóveda\n\nGuarda la relación entre token y PAN.\n\n## Cifrado\n\nEs reversible con la clave.\n"
    pieces = StructuralSplitter().split_with_sections(text)
    assert [p.section for p in pieces] == ["Título > Bóveda", "Título > Cifrado"]
    assert pieces[0].text.startswith("# Título\n\n## Bóveda") and "Cifrado" not in pieces[0].text


def test_subtitulos_repetidos_conservan_sus_titulos_padre():
    text = (
        "# Planes\n\n## Gratuito\n\n### Usuarios\n\nSe permite 1 usuario.\n\n"
        "## Premium\n\n### Usuarios\n\nSe permiten 10 usuarios.\n"
    )
    pieces = StructuralSplitter().split_with_sections(text)
    assert [p.section for p in pieces] == [
        "Planes > Gratuito > Usuarios", "Planes > Premium > Usuarios",
    ]
    assert pieces[0].text.startswith("# Planes\n\n## Gratuito\n\n### Usuarios")
    assert pieces[1].text.startswith("# Planes\n\n## Premium\n\n### Usuarios")
    assert "Premium" not in pieces[0].text and "Gratuito" not in pieces[1].text
    assert text[pieces[0].start:pieces[0].end] == "### Usuarios\n\nSe permite 1 usuario."


def test_seccion_extensa_repite_contexto_sin_arrastrar_titulos_anteriores():
    text = (
        "# Manual\n\n## Anterior\n\nTexto previo.\n\n"
        "## Actual\n\n### Requisitos\n\n" + TECH_TEXT * 30
        + "\n\n# Otro manual\n\n## Requisitos\n\nTexto final.\n"
    )
    pieces = StructuralSplitter(chunk_size=100, chunk_overlap=15).split_with_sections(text)
    requisitos = [p for p in pieces if p.section == "Manual > Actual > Requisitos"]
    assert len(requisitos) > 1
    assert all(p.text.startswith("# Manual\n\n## Actual\n\n### Requisitos") for p in requisitos)
    assert all("Anterior" not in p.text for p in requisitos)
    assert pieces[-1].section == "Otro manual > Requisitos"
    assert pieces[-1].text.startswith("# Otro manual\n\n## Requisitos")
    assert "## Actual" not in pieces[-1].text


def test_titulos_padre_no_alteran_las_paginas_del_contenido():
    chunks = perform_structural_chunking("doc-x", [
        content("# Manual\n\n## Gratuito", page=1),
        content("### Usuarios\n\nSe permite 1 usuario.", page=2),
    ])
    assert len(chunks) == 1
    assert chunks[0].metadata.section == "Manual > Gratuito > Usuarios"
    assert chunks[0].metadata.page == chunks[0].metadata.page_end == 2
    assert chunks[0].text.startswith("# Manual\n\n## Gratuito\n\n### Usuarios")


def test_texto_sin_titulos_agrupa_parrafos(monkeypatch):
    monkeypatch.setattr(structural_splitter, "PARAGRAPH_GROUP_TOKENS", 50)  # ~2 párrafos por grupo
    parrafos = [f"Párrafo {n} con contenido técnico sobre logística y entregas." * 2 for n in range(4)]
    pieces = StructuralSplitter().split_with_sections("\n\n".join(parrafos))
    assert 1 < len(pieces) < 4
    assert all(p.text.strip().startswith("Párrafo") for p in pieces)  # no corta párrafos a la mitad
    assert "".join(p.text for p in pieces).replace("\n", "") == "".join(parrafos)


def test_bloque_de_codigo_con_lineas_en_blanco_no_se_parte(monkeypatch):
    monkeypatch.setattr(structural_splitter, "PARAGRAPH_GROUP_TOKENS", 5)
    text = "Texto previo con varias palabras de contexto.\n\n```bash\ngit switch main\n\ngit merge rama\n```\n\nTexto final."
    pieces = StructuralSplitter().split_with_sections(text)
    assert any("git switch main\n\ngit merge rama" in p.text for p in pieces)
    assert all(p.text.count("```") % 2 == 0 for p in pieces)
    assert "Texto final." in pieces[-1].text  # no se pierde contenido alrededor del bloque


def test_titulo_aislado_no_genera_chunk():
    pieces = StructuralSplitter().split_with_sections("## Tokens\n\n" + "Firma del token JWT. " * 400)
    assert all(piece.text.strip() != "## Tokens" for piece in pieces)
    assert all(piece.section == "Tokens" for piece in pieces)


def test_chunking_cruza_paginas_y_registra_pagina_final(monkeypatch):
    monkeypatch.setattr(structural_splitter, "enrich_chunks_metadata", lambda texts: [INFO] * len(texts))
    page_1 = "\n\n".join(f"Párrafo {n} sobre la firma del token JWT y su validación en el servidor. " * 3 for n in range(12))
    page_2 = "\n\n".join(f"Párrafo {n} de la segunda página. " * 5 for n in range(12, 18))
    pages = [content("## Tokens\n\n" + page_1, page=1), content(page_2, page=2)]
    chunks = perform_structural_chunking("doc-x", pages)
    assert chunks[0].metadata.page == 1
    assert chunks[-1].metadata.page_end == 2
    assert any(c.metadata.page == 1 and c.metadata.page_end == 2 for c in chunks)
    assert all(c.metadata.section == "Tokens" for c in chunks)
    assert [c.metadata.chunk_id for c in chunks] == [f"doc-x-chk-{i:04d}" for i in range(1, len(chunks) + 1)]


def test_enriquecimiento_por_lotes_cache_y_reintento(monkeypatch):
    calls = []
    monkeypatch.setattr(structural_splitter, "BATCH_SIZE", 2)

    def fake_batch(texts):
        calls.append(list(texts))
        return {0: INFO}  # omite el segundo fragmento de cada lote

    monkeypatch.setattr(structural_splitter, "_enrich_batch", fake_batch)
    texts = ["uno", "dos", "tres"]
    assert structural_splitter.enrich_chunks_metadata(texts) == [INFO, INFO, INFO]
    # Los omitidos se reintentan juntos en una llamada (antes, uno por uno y en serie).
    # Los lotes corren en paralelo: el orden de las llamadas no está garantizado.
    assert sorted(calls) == [["dos"], ["tres"], ["uno", "dos"]]

    calls.clear()
    structural_splitter.enrich_chunks_metadata(["uno", "tres"])
    assert calls == []  # ambos quedaron en caché


def test_enriquecimiento_clasifica_lotes_en_paralelo(monkeypatch):
    import threading

    monkeypatch.setenv("IA_STRICT_PROVIDERS", "1")
    monkeypatch.setattr(structural_splitter, "BATCH_SIZE", 1)
    monkeypatch.setattr(structural_splitter, "CONCURRENCY", 2)
    # Solo se libera si dos lotes están en curso a la vez; en serie, vence y falla.
    barrier = threading.Barrier(2, timeout=5)

    def fake_batch(texts):
        barrier.wait()
        return {0: INFO}

    monkeypatch.setattr(structural_splitter, "_enrich_batch", fake_batch)
    assert structural_splitter.enrich_chunks_metadata(["uno", "dos"]) == [INFO, INFO]


def test_enriquecimiento_clasifica_una_vez_los_textos_repetidos(monkeypatch):
    calls = []
    monkeypatch.setattr(structural_splitter, "_enrich_batch", lambda texts: calls.append(list(texts)) or {i: INFO for i in range(len(texts))})
    assert structural_splitter.enrich_chunks_metadata(["uno", "uno", "dos"]) == [INFO, INFO, INFO]
    assert calls == [["uno", "dos"]]


@pytest.mark.parametrize("estricto", [False, True])
def test_enriquecimiento_sin_proveedor_no_corta_la_solicitud(monkeypatch, estricto):
    # La clase solo ordena prioridades al seleccionar contexto: un 503 en un lote
    # no debe hacer fallar la adaptación completa, tampoco en modo estricto.
    if estricto:
        monkeypatch.setenv("IA_STRICT_PROVIDERS", "1")

    def fail(_texts):
        raise ConnectionError("sin red")

    monkeypatch.setattr(structural_splitter, "_enrich_batch", fail)
    assert structural_splitter.enrich_chunks_metadata(["uno"])[0].concepto_principal == "General"
    # La clase por defecto no se guarda en caché: con proveedor disponible se clasifica.
    monkeypatch.setattr(structural_splitter, "_enrich_batch", lambda texts: {0: INFO})
    assert structural_splitter.enrich_chunks_metadata(["uno"]) == [INFO]


def test_chunking_no_llama_al_proveedor(monkeypatch):
    monkeypatch.setattr(structural_splitter, "_enrich_batch", lambda _texts: pytest.fail("El chunking ya no clasifica"))
    chunks = perform_structural_chunking("doc-x", [content("## JWT\n\n" + TECH_TEXT * 5)])
    assert chunks and all(c.metadata.tipo_contenido == "afirmacion" for c in chunks)


def _pdf(path, paginas, texto=TECH_TEXT):
    document = pymupdf.open()
    for _ in range(paginas):
        document.new_page().insert_text((72, 72), texto)
    document.save(path)
    document.close()


def test_pdf_con_demasiadas_paginas_se_rechaza_antes_de_extraer(tmp_path, monkeypatch):
    monkeypatch.setenv("IA_MAX_PAGINAS", "3")
    monkeypatch.setattr(ingestion, "_extract_pdf", lambda *_a: pytest.fail("No debe extraer"))
    _pdf(tmp_path / "libro.pdf", 4)
    result = ingestion.ingest_document(str(tmp_path / "libro.pdf"))
    assert (result.status, result.codigo) == ("rechazado", "DOCUMENTO_DEMASIADO_EXTENSO")


def test_texto_demasiado_extenso_se_rechaza_en_cualquier_formato(tmp_path, monkeypatch):
    monkeypatch.setenv("IA_MAX_TOKENS_DOCUMENTO", "100")
    path = tmp_path / "largo.md"
    path.write_text(TECH_TEXT * 10, encoding="utf-8")
    result = ingestion.ingest_document(str(path))
    assert (result.status, result.codigo) == ("rechazado", "DOCUMENTO_DEMASIADO_EXTENSO")


def test_pdf_pesado_con_pocas_paginas_se_acepta(tmp_path):
    # El límite es de contenido, no de bytes: una imagen grande no cuenta como texto.
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), TECH_TEXT)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 1500, 1500), False)
    page.insert_image(page.rect, pixmap=pix)
    document.save(tmp_path / "pesado.pdf")
    document.close()
    assert ingestion.ingest_document(str(tmp_path / "pesado.pdf")).status == "aprobado"


def test_extraccion_de_pdf_se_reutiliza_por_hash(tmp_path, monkeypatch):
    _pdf(tmp_path / "a.pdf", 2)
    first = ingestion.ingest_document(str(tmp_path / "a.pdf"), document_name="original.pdf")
    monkeypatch.setattr(ingestion, "_extract_pdf", lambda *_a: pytest.fail("Debe usar la caché"))
    second = ingestion.ingest_document(str(tmp_path / "a.pdf"), document_name="otro-nombre.pdf")
    assert [c.text for c in second.content] == [c.text for c in first.content]
    assert [c.metadata.page for c in second.content] == [1, 2]
    assert second.content[0].metadata.name == "otro-nombre.pdf"


@pytest.mark.parametrize("texto", [
    # Sectores sin vocabulario informático: antes se rechazaban con DOCUMENTO_NO_TECNICO.
    "El embudo de conversión mide cuántos visitantes avanzan desde el anuncio hasta la compra. "
    "Una campaña con segmentación por intereses reduce el costo por adquisición.",
    "La hipertensión arterial se diagnostica con dos mediciones elevadas en consultas distintas. "
    "El tratamiento inicial combina cambios en la dieta y actividad física.",
    "A Java class can extend only one superclass but implement multiple interfaces. "
    "Static methods belong to the class rather than to an instance.",
])
def test_documentos_de_cualquier_sector_e_idioma_se_aceptan(tmp_path, texto):
    path = tmp_path / "documento.md"
    path.write_text(texto, encoding="utf-8")
    assert ingestion.ingest_document(str(path)).status == "aprobado"


def test_documento_no_apto_segun_el_modelo_se_rechaza(tmp_path, monkeypatch):
    monkeypatch.setattr(enrichment, "enrich_document_metadata", lambda doc_id, _text:
        enrichment.DocumentPedagogicalMetadata(document_id=doc_id, apto_para_aprendizaje=False))
    path = tmp_path / "documento.md"
    path.write_text("Hola, ¿nos vemos mañana a las 8? Llevo las entradas del cine y algo para comer.", encoding="utf-8")
    result = ingestion.ingest_document(str(path))
    assert (result.status, result.codigo) == ("rechazado", "DOCUMENTO_NO_APTO")


def test_metadata_en_cache_anterior_se_considera_apta():
    # Las cachés creadas antes de este campo no lo tienen y no deben rechazar documentos ya procesados.
    assert enrichment.DocumentPedagogicalMetadata(document_id="doc-x").apto_para_aprendizaje is True


def test_document_id_estable_y_nombre_original(tmp_path):
    path = tmp_path / "documento.md"
    path.write_text(TECH_TEXT * 3, encoding="utf-8")
    first = ingestion.ingest_document(str(path), document_name="JWT en OCI.md")
    second = ingestion.ingest_document(str(path))
    assert first.status == "aprobado"
    assert first.document_id == second.document_id
    assert first.content[0].metadata.name == "JWT en OCI.md"


def test_extraccion_pdf_por_pagina(tmp_path):
    path = tmp_path / "doc.pdf"
    pdf = pymupdf.open()
    for number in (1, 2):
        pdf.new_page().insert_text((72, 72), f"Pagina {number}: {TECH_TEXT}"[:90])
    pdf.save(str(path))
    pdf.close()
    pages = ingestion._extract_pdf(str(path), "doc-x", "doc.pdf")
    assert [p.metadata.page for p in pages] == [1, 2]
    assert "Pagina 2" in pages[1].text


def test_pagina_con_markdown_incompleto_usa_texto_plano(tmp_path, monkeypatch):
    import pymupdf4llm

    path = tmp_path / "doc.pdf"
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Arquitectura de red con subredes privadas y gateways")
    pdf.save(str(path))
    pdf.close()
    # Simula el caso real: pymupdf4llm omite el texto superpuesto a una imagen
    monkeypatch.setattr(pymupdf4llm, "to_markdown", lambda *_a, **_k: "29/9/26 encabezado")
    pages = ingestion._extract_pdf(str(path), "doc-x", "doc.pdf")
    assert "subredes privadas" in pages[0].text


def test_encabezados_repetidos_y_enlaces():
    bodies = ["\n".join(f"Paso {n}{i}: configurar la subred" for i in range(1, 9)) for n in range(1, 5)]
    texts = [f"29/9/26, 17:05 VCN\n{body}\nhttps://docs.example/x {n}/4" for n, body in enumerate(bodies, start=1)]
    cleaned = ingestion._remove_repeated_lines(texts)
    # Se eliminan encabezado y pie; el cuerpo se conserva aunque sus líneas solo difieran en números
    assert cleaned == bodies
    assert ingestion._MARKDOWN_LINK.sub(r"\1", "Ver [la VCN](https://a.b/c?x=(1)) ahora") == "Ver la VCN ahora"


class FakeStore:
    def __init__(self):
        self.rows = {}
        self.added = 0

    def get(self, where, include):
        ids = [i for i, (_, meta) in self.rows.items() if meta["document_id"] == where["document_id"]]
        return {"ids": ids, "documents": [self.rows[i][0] for i in ids], "metadatas": [self.rows[i][1] for i in ids]}

    def delete(self, ids):
        for i in ids:
            self.rows.pop(i)

    def add_documents(self, documents, ids):
        self.added += len(documents)
        for i, doc in zip(ids, documents):
            self.rows[i] = (doc.page_content, doc.metadata)


def make_chunks(*texts):
    return [
        Chunk(text=t, metadata=ChunkMetadata(document_id="doc-x", chunk_id=f"doc-x-chk-{i:04d}", name="a", doc_type="md", section="S"))
        for i, t in enumerate(texts, start=1)
    ]


def test_indexacion_idempotente(monkeypatch):
    store = FakeStore()
    monkeypatch.setattr(client, "get_vector_store", lambda: store)
    assert client.insert_chunks(make_chunks("a", "b")) is False
    assert client.insert_chunks(make_chunks("a", "b")) is True
    assert store.added == 2  # no se recalcularon embeddings
    assert client.insert_chunks(make_chunks("a")) is False
    assert list(store.rows) == ["doc-x-chk-0001"]  # se eliminaron los vectores obsoletos
    assert [d.page_content for d in client.get_document_chunks("doc-x")] == ["a"]


def test_registro_documento():
    meta = enrichment.DocumentPedagogicalMetadata(document_id="doc-x", conceptos_clave=["JWT"])
    client.save_document_record("doc-x", make_chunks("a", "b"), meta)
    record = client.load_document_record("doc-x")
    assert record["chunks"] == 2
    assert record["sections"] == ["S"]
    assert record["pedagogical_metadata"]["conceptos_clave"] == ["JWT"]
    assert client.load_document_record("doc-otro") is None


def test_sin_embeddings_los_fragmentos_se_leen_del_registro(monkeypatch):
    from dataia.common.models import ChunkingResult
    from dataia.vectorstore.service import process_vectorstore

    monkeypatch.delenv("DATAIA_EMBEDDINGS_ENABLED", raising=False)
    monkeypatch.setattr(client, "get_vector_store", lambda: pytest.fail("Sin embeddings no se usa Chroma"))
    chunking = ChunkingResult(document_id="doc-x", chunks=make_chunks("b", "a"))
    first = process_vectorstore(chunking)
    assert (first.status, first.already_indexed) == ("aprobado", False)
    assert process_vectorstore(chunking).already_indexed is True
    stored = client.get_document_chunks("doc-x")
    assert [d.page_content for d in stored] == ["b", "a"]  # orden del documento
    assert stored[0].metadata["section"] == "S"


def test_con_embeddings_se_indexa_en_chroma(monkeypatch):
    from dataia.common.models import ChunkingResult
    from dataia.vectorstore.service import process_vectorstore

    monkeypatch.setenv("DATAIA_EMBEDDINGS_ENABLED", "true")
    store = FakeStore()
    monkeypatch.setattr(client, "get_vector_store", lambda: store)
    assert process_vectorstore(ChunkingResult(document_id="doc-x", chunks=make_chunks("a", "b"))).status == "aprobado"
    assert store.added == 2


@pytest.mark.parametrize("filename", ["JWT en OCI.pdf", "Arquitectura de microservicios.pdf", "VCN y subredes.pdf"])
def test_pdf_fixtures_keep_sections_and_document_coverage(monkeypatch, filename):
    monkeypatch.setattr(structural_splitter, "enrich_chunks_metadata", lambda texts: [INFO] * len(texts))
    path = Path(__file__).resolve().parents[2] / "nuevamente-ai-core" / "tests" / filename
    ingested = ingestion.ingest_document(str(path))
    assert ingested.status == "aprobado"
    chunks = perform_structural_chunking(ingested.document_id, ingested.content)
    assert any(c.metadata.section for c in chunks)
    assert any(c.metadata.page_end > c.metadata.page for c in chunks)
    with pymupdf.open(path) as document:
        plain = " ".join(page.get_text("text") for page in document)
    words = lambda text: {w for w in re.findall(r"[^\W_]+", text.lower()) if len(w) > 3 and not w.isdigit()}
    source_words = words(plain)
    recovered_words = words(" ".join(c.text for c in chunks))
    assert len(source_words & recovered_words) / len(source_words) >= 0.9
