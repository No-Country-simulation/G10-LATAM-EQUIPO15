"""Recuperación de registros y guardado seguro, sin red ni proveedores de IA."""

import json
from pathlib import Path

import pytest

from dataia.common.models import Chunk, ChunkMetadata, ChunkingResult
from dataia.vectorstore import client
from dataia.vectorstore.service import process_vectorstore


@pytest.fixture(autouse=True)
def offline_records(monkeypatch, tmp_path):
    monkeypatch.setattr(client, "DOCUMENTS_DIRECTORY", str(tmp_path / "documents"))
    monkeypatch.setenv("DATAIA_EMBEDDINGS_ENABLED", "false")
    monkeypatch.setattr(client, "get_vector_store", lambda: pytest.fail("No debe usar Chroma ni embeddings"))


def chunking(text="Contenido original."):
    return ChunkingResult(document_id="doc-x", chunks=[Chunk(
        text=text,
        metadata=ChunkMetadata(document_id="doc-x", chunk_id="doc-x-chk-0001", name="manual.md", doc_type="md"),
    )])


@pytest.mark.parametrize("damaged", [b'{"document_id":', b"", b"[]", b"[1]", b"\xff"])
def test_reingesta_recupera_registro_incompleto_y_permite_reutilizarlo(damaged):
    path = Path(client._document_record_path("doc-x"))
    path.parent.mkdir(parents=True)
    path.write_bytes(damaged)

    first = process_vectorstore(chunking())
    assert first.status == "aprobado"
    assert first.already_indexed is False
    assert client.load_document_record("doc-x")["document_id"] == "doc-x"
    assert client.get_document_chunks("doc-x")[0].page_content == "Contenido original."
    second = process_vectorstore(chunking())
    assert second.status == "aprobado" and second.already_indexed is True


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("interruption", [OSError, KeyboardInterrupt])
def test_escritura_interrumpida_no_publica_un_registro_parcial(monkeypatch, existing, interruption):
    path = Path(client._document_record_path("doc-x"))
    if existing:
        assert process_vectorstore(chunking()).status == "aprobado"
    original = path.read_bytes() if existing else None

    def interrupted_dump(_record, stream, **_kwargs):
        stream.write('{"document_id":')
        stream.flush()
        raise interruption("interrupción simulada durante la escritura")

    with monkeypatch.context() as patch:
        patch.setattr(client.json, "dump", interrupted_dump)
        with pytest.raises(interruption):
            client.save_document_record("doc-x", chunking("Contenido nuevo.").chunks, None)

    if existing:
        assert path.read_bytes() == original
        assert json.loads(path.read_text(encoding="utf-8"))["document_id"] == "doc-x"
    else:
        assert not path.exists()
    assert not list(path.parent.glob("*.tmp"))
    assert process_vectorstore(chunking("Contenido nuevo.")).status == "aprobado"
    assert client.get_document_chunks("doc-x")[0].page_content == "Contenido nuevo."


def test_fallo_al_reemplazar_conserva_el_registro_anterior(monkeypatch):
    assert process_vectorstore(chunking()).status == "aprobado"
    path = Path(client._document_record_path("doc-x"))
    original = path.read_bytes()

    def failed_replace(_source, _destination):
        raise OSError("reemplazo no disponible")

    with monkeypatch.context() as patch:
        patch.setattr(client.os, "replace", failed_replace)
        with pytest.raises(OSError, match="reemplazo no disponible"):
            client.save_document_record("doc-x", chunking("Contenido nuevo.").chunks, None)
    assert path.read_bytes() == original
    assert not list(path.parent.glob("*.tmp"))


def test_registro_anterior_sin_fragmentos_se_puede_actualizar():
    path = Path(client._document_record_path("doc-x"))
    path.parent.mkdir(parents=True)
    legacy = {"document_id": "doc-x", "chunks": 1, "sections": ["Manual"]}
    path.write_text(json.dumps(legacy), encoding="utf-8")
    assert client.load_document_record("doc-x") == legacy
    result = process_vectorstore(chunking())
    assert result.status == "aprobado" and result.already_indexed is False
    assert client.load_document_record("doc-x")["chunk_records"]


def test_error_de_permisos_no_se_confunde_con_registro_danado(monkeypatch):
    assert process_vectorstore(chunking()).status == "aprobado"

    def denied_open(*_args, **_kwargs):
        raise PermissionError("lectura no permitida")

    monkeypatch.setattr(client, "open", denied_open, raising=False)
    with pytest.raises(PermissionError, match="lectura no permitida"):
        client.load_document_record("doc-x")
