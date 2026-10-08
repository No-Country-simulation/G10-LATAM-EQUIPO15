"""
Pruebas unitarias offline y deterministas para el módulo de contexto pedagógico (Fase B).
Valida selección por formato, presupuesto de tokens, preservación de secciones y formateo etiquetado.
"""

from unittest.mock import MagicMock
from langchain_core.documents import Document

from src.ai.contexto import (
    seleccionar_fragmentos,
    formatear_texto_fuente_etiquetado,
    obtener_registro_documento,
    obtener_chunks_documento,
)


def _crear_doc(chunk_id: str, text: str, section: str = "Sec1", page: int = 1, page_end: int = 1, tipo: str = "afirmacion"):
    return Document(
        page_content=text,
        metadata={
            "chunk_id": chunk_id,
            "section": section,
            "page": page,
            "page_end": page_end,
            "tipo_contenido": tipo,
            "document_id": "doc-test"
        }
    )


def test_seleccionar_fragmentos_dentro_del_presupuesto_entrega_todos():
    chunks = [
        _crear_doc("doc-test-chk-0001", "Definición de VCN", section="Intro", tipo="definicion"),
        _crear_doc("doc-test-chk-0002", "Paso a paso para subredes", section="Config", tipo="procedimiento"),
        _crear_doc("doc-test-chk-0003", "Reglas de firewall", section="Seguridad", tipo="afirmacion"),
    ]
    res = seleccionar_fragmentos(chunks, formato="Flashcards", presupuesto_tokens=1000)
    assert len(res) == 3
    assert [r["id"] for r in res] == ["F1", "F2", "F3"]
    assert res[0]["section"] == "Intro"
    assert res[0]["tipo_contenido"] == "definicion"


def test_seleccionar_fragmentos_prioriza_por_formato_flashcards():
    chunks = [
        _crear_doc("chk-1", "Texto largo de ejemplo " * 40, section="S1", tipo="ejemplo"),
        _crear_doc("chk-2", "Definición clave " * 20, section="S1", tipo="definicion"),
        _crear_doc("chk-3", "Procedimiento largo " * 40, section="S2", tipo="procedimiento"),
        _crear_doc("chk-4", "Definición de S2 " * 20, section="S2", tipo="definicion"),
    ]
    # Presupuesto ajustado que no permite los 4 chunks
    res = seleccionar_fragmentos(chunks, formato="Flashcards", presupuesto_tokens=80)
    # Debe priorizar las definiciones de cada sección
    tipos = [r["tipo_contenido"] for r in res]
    assert "definicion" in tipos


def test_seleccionar_fragmentos_garantiza_cobertura_de_secciones():
    chunks = [
        _crear_doc("chk-1", "Sección 1 texto " * 10, section="Arquitectura"),
        _crear_doc("chk-2", "Sección 2 texto " * 10, section="Seguridad"),
        _crear_doc("chk-3", "Sección 3 texto " * 10, section="Despliegue"),
    ]
    res = seleccionar_fragmentos(chunks, formato="Resumen Ejecutivo", presupuesto_tokens=100)
    secciones = {r["section"] for r in res}
    assert secciones == {"Arquitectura", "Seguridad", "Despliegue"}


def test_formatear_texto_fuente_etiquetado():
    frags = [
        {
            "id": "F1",
            "chunk_id": "doc-chk-01",
            "page": 1,
            "page_end": 2,
            "section": "Conceptos",
            "contenido": "Una VCN es una red privada virtual."
        },
        {
            "id": "F2",
            "chunk_id": "doc-chk-02",
            "page": 3,
            "page_end": 3,
            "section": "Subredes",
            "contenido": "Las subredes dividen la VCN."
        }
    ]
    texto = formatear_texto_fuente_etiquetado(frags)
    assert "[F1 | doc-chk-01 | págs. 1–2 | Sección: Conceptos]" in texto
    assert "[F2 | doc-chk-02 | pág. 3 | Sección: Subredes]" in texto
    assert "Una VCN es una red privada virtual." in texto


def test_obtener_registro_documento_lee_disco_o_fallback(monkeypatch):
    from dataia.vectorstore import client
    registro_falso = {
        "document_id": "doc-123",
        "sections": ["S1", "S2"],
        "pedagogical_metadata": {
            "conceptos_clave": ["VCN", "Subred"],
            "prerrequisitos": ["Cuenta OCI"],
            "resumen_ejecutivo": "Resumen técnico de OCI."
        }
    }
    monkeypatch.setattr(client, "load_document_record", lambda doc_id: registro_falso if doc_id == "doc-123" else None)
    
    meta = obtener_registro_documento("doc-123")
    assert meta["conceptos_clave"] == ["VCN", "Subred"]
    assert meta["prerrequisitos"] == ["Cuenta OCI"]
    assert meta["secciones"] == ["S1", "S2"]
    
    # Fallback si no está en disco
    mock_ingesta = MagicMock()
    mock_ingesta.pedagogical_metadata.conceptos_clave = ["TerminoFallback"]
    meta_fb = obtener_registro_documento("doc-inexistente", ingestion_res=mock_ingesta)
    assert meta_fb["conceptos_clave"] == ["TerminoFallback"]
