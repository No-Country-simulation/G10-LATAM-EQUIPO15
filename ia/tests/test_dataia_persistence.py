"""Comprueba reutilización real de Chroma y caché entre procesos nuevos, sin red."""

import multiprocessing


def _index_document(connection, directory):
    import os
    from pathlib import Path
    from types import SimpleNamespace

    base = Path(directory)
    os.environ["CHROMADB_DIR"] = str(base / "chroma")
    os.environ["DATAIA_DOCUMENTS_DIR"] = str(base / "documents")
    os.environ["DATAIA_CACHE_DIR"] = str(base / "cache")
    os.environ["IA_STRICT_PROVIDERS"] = "1"
    from langchain_core.embeddings import Embeddings
    from dataia.ingestion import enrichment
    from dataia.ingestion.service import ingest_document
    from dataia.chunking import structural_splitter
    from dataia.chunking.service import process_chunks
    from dataia.vectorstore import client
    from dataia.vectorstore.service import process_vectorstore

    calls = {"llm":0, "embeddings":0}

    class OfflineEmbeddings(Embeddings):
        def embed_documents(self, texts):
            calls["embeddings"] += 1
            return [[0.1, 0.2, 0.3] for _ in texts]

        def embed_query(self, text):
            raise AssertionError("La lectura secuencial no requiere un embedding de consulta.")

    class OfflineLLM:
        def with_structured_output(self, schema):
            def invoke(_prompt):
                calls["llm"] += 1
                if schema.__name__ == "DocumentPedagogicalMetadata":
                    return schema(document_id="replaced", conceptos_clave=["JWT"])
                return schema(fragmentos=[{
                    "indice":0, "tipo_contenido":"definicion", "nivel_dificultad":2,
                    "concepto_principal":"JWT",
                }])
            return SimpleNamespace(invoke=invoke)

    enrichment.create_gemini_llm = lambda **_kwargs: OfflineLLM()
    structural_splitter.create_gemini_llm = lambda **_kwargs: OfflineLLM()
    client.get_embeddings_model = lambda: OfflineEmbeddings()
    try:
        ingested = ingest_document(str(base / "jwt.md"))
        assert ingested.status == "aprobado"
        chunked = process_chunks(ingested)
        assert chunked.status == "aprobado"
        indexed = process_vectorstore(chunked)
        assert indexed.status == "aprobado"
        stored = client.get_document_chunks(ingested.document_id)
        record = client.load_document_record(ingested.document_id)
        connection.send({
            "document_id":ingested.document_id, "already_indexed":indexed.already_indexed,
            "chunk_ids":[d.metadata["chunk_id"] for d in stored], "calls":calls,
            "concepts":record["pedagogical_metadata"]["conceptos_clave"],
        })
    finally:
        connection.close()


def _fresh_process(directory):
    context = multiprocessing.get_context("spawn")
    receiving, sending = context.Pipe(duplex=False)
    process = context.Process(target=_index_document, args=(sending, str(directory)))
    try:
        process.start()
        sending.close()
        assert receiving.poll(20), "El proceso de indexación no respondió."
        result = receiving.recv()
        process.join(timeout=3)
        assert process.exitcode == 0
        return result
    finally:
        receiving.close()
        sending.close()
        if process.is_alive():
            process.terminate()
            process.join(timeout=3)
        process.close()


def test_same_document_reuses_cache_and_vectors_after_process_restart(tmp_path):
    (tmp_path / "jwt.md").write_text(
        "# JWT\n\nLa arquitectura del sistema usa una API con token JWT "
        "para la seguridad del servidor en la nube.\n", encoding="utf-8",
    )
    first = _fresh_process(tmp_path)
    second = _fresh_process(tmp_path)
    assert first["document_id"] == second["document_id"]
    assert first["already_indexed"] is False
    assert second["already_indexed"] is True
    assert first["chunk_ids"] == second["chunk_ids"]
    assert len(first["chunk_ids"]) == 1
    assert first["calls"] == {"llm":2, "embeddings":1}
    assert second["calls"] == {"llm":0, "embeddings":0}
    assert second["concepts"] == ["JWT"]
