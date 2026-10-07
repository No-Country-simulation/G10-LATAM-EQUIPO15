"""
Módulo de contexto y selección pedagógica para NuevaMente AI Core.
Adapta la lectura de DataIA (Fase A) seleccionando fragmentos según formato
y presupuesto de tokens, con trazabilidad jerárquica (sección, página, tipo).
"""

import logging
from typing import Any, Dict, List, Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Presupuesto predeterminado de tokens de contexto para la llamada al LLM
PRESUPUESTO_TOKENS_DEFAULT = 24000


def _obtener_cliente_vectorstore():
    """Importa el cliente de VectorStore soportando tanto 'dataia' como 'src.dataia'."""
    try:
        from dataia.vectorstore import client
        return client
    except ImportError:
        try:
            from src.dataia.vectorstore import client
            return client
        except ImportError as e:
            logger.error("No se pudo importar dataia.vectorstore.client: %s", e)
            raise


def obtener_chunks_documento(document_id: str) -> List[Document]:
    """
    Recupera todos los chunks del documento en su orden original.
    Prioriza get_document_chunks (Fase A); si no existe o falla, recurre a Chroma directo.
    """
    client = _obtener_cliente_vectorstore()
    if hasattr(client, "get_document_chunks"):
        try:
            chunks = client.get_document_chunks(document_id)
            if chunks:
                return chunks
        except Exception as e:
            logger.warning("Fallo al invocar get_document_chunks: %s. Reintentando vía Chroma directo.", e)

    # Fallback directo a ChromaDB
    vs = client.get_vector_store()
    res = vs.get(where={"document_id": document_id}, include=["documents", "metadatas"])
    documents = [
        Document(page_content=text, metadata=meta or {})
        for text, meta in zip(res.get("documents", []), res.get("metadatas", []))
    ]
    return sorted(documents, key=lambda d: str(d.metadata.get("chunk_id", "")))


def obtener_registro_documento(
    document_id: str,
    ingestion_res: Optional[Any] = None,
    chunking_res: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Recupera la metadata pedagógica consolidada (conceptos clave, prerrequisitos, resumen)
    desde el registro persistido en disco (Fase A), ChunkingResult o IngestionResult.
    """
    client = _obtener_cliente_vectorstore()
    record = None
    if hasattr(client, "load_document_record"):
        try:
            record = client.load_document_record(document_id)
        except Exception as e:
            logger.debug("No se pudo cargar el registro de documento desde disco: %s", e)

    ped_meta = None
    secciones = []
    if record:
        ped_meta = record.get("pedagogical_metadata") or {}
        secciones = record.get("sections") or []
    else:
        # Fallback a objetos en memoria de la pipeline
        ped_obj = (
            getattr(chunking_res, "pedagogical_metadata", None)
            or getattr(ingestion_res, "pedagogical_metadata", None)
        )
        if ped_obj:
            if isinstance(ped_obj, dict):
                ped_meta = ped_obj
            elif hasattr(ped_obj, "model_dump") and callable(getattr(ped_obj, "model_dump")):
                try:
                    res = ped_obj.model_dump()
                    ped_meta = res if isinstance(res, dict) else None
                except Exception:
                    ped_meta = None
            if not isinstance(ped_meta, dict):
                ped_meta = {
                    "conceptos_clave": getattr(ped_obj, "conceptos_clave", []),
                    "prerrequisitos": getattr(ped_obj, "prerrequisitos", []),
                    "resumen_ejecutivo": getattr(ped_obj, "resumen_ejecutivo", "")
                }

    conceptos = list((ped_meta or {}).get("conceptos_clave") or [])
    prerrequisitos = list((ped_meta or {}).get("prerrequisitos") or [])
    resumen = (ped_meta or {}).get("resumen_ejecutivo") or ""

    return {
        "document_id": document_id,
        "conceptos_clave": conceptos,
        "prerrequisitos": prerrequisitos,
        "resumen_ejecutivo": resumen,
        "secciones": secciones,
    }


def _estimar_tokens(texto: str) -> int:
    """Estimación conservadora del número de tokens (aprox. 1 token cada 3.5 caracteres o 1.3 por palabra)."""
    if not texto:
        return 0
    return max(1, int(len(texto.split()) * 1.3))


def seleccionar_fragmentos(
    chunks: List[Document],
    formato: str,
    presupuesto_tokens: int = PRESUPUESTO_TOKENS_DEFAULT
) -> List[Dict[str, Any]]:
    """
    Selecciona fragmentos respetando el formato didáctico y el presupuesto de tokens:
    - Si el documento completo cabe en el presupuesto, se entrega completo en su orden original.
    - Si supera el presupuesto, prioriza por tipo_contenido y garantiza cobertura por sección.
    Retorna lista de diccionarios con id 'F1'..'Fn' y metadatos pedagógicos.
    """
    if not chunks:
        return []

    tokens_totales = sum(_estimar_tokens(c.page_content) for c in chunks)

    # Caso 1: Todo el documento cabe en el presupuesto
    if tokens_totales <= presupuesto_tokens:
        chunks_seleccionados = list(chunks)
    else:
        # Caso 2: Selección estructurada por formato y sección
        fmt = (formato or "").lower()
        if "flashcard" in fmt:
            prioridad_tipos = ["definicion", "afirmacion", "procedimiento", "ejemplo", "codigo", "tabla"]
        elif "quiz" in fmt:
            prioridad_tipos = ["afirmacion", "procedimiento", "definicion", "ejemplo", "codigo", "tabla"]
        elif "guia" in fmt or "tutorial" in fmt:
            prioridad_tipos = ["procedimiento", "codigo", "ejemplo", "definicion", "afirmacion", "tabla"]
        else:  # Resumen, Mapa Mental, etc.
            prioridad_tipos = ["definicion", "afirmacion", "procedimiento", "ejemplo", "codigo", "tabla"]

        # Agrupar por sección
        por_seccion: Dict[str, List[Document]] = {}
        for c in chunks:
            sec = str(c.metadata.get("section") or "General")
            por_seccion.setdefault(sec, []).append(c)

        seleccionados_set = set()
        presupuesto_restante = presupuesto_tokens

        # Fase A de selección: al menos 1 chunk por sección (para cobertura completa del documento)
        for sec, items_sec in por_seccion.items():
            # Ordenar items de la sección según prioridad de tipo
            items_ordenados = sorted(
                items_sec,
                key=lambda x: prioridad_tipos.index(x.metadata.get("tipo_contenido", "afirmacion"))
                if x.metadata.get("tipo_contenido") in prioridad_tipos else 99
            )
            elegido = items_ordenados[0]
            cid = elegido.metadata.get("chunk_id") or elegido.page_content
            seleccionados_set.add(cid)
            presupuesto_restante -= _estimar_tokens(elegido.page_content)

        # Fase B de selección: completar con los chunks de mayor prioridad hasta agotar presupuesto
        todos_restantes = [
            c for c in chunks
            if (c.metadata.get("chunk_id") or c.page_content) not in seleccionados_set
        ]
        todos_restantes_ordenados = sorted(
            todos_restantes,
            key=lambda x: prioridad_tipos.index(x.metadata.get("tipo_contenido", "afirmacion"))
            if x.metadata.get("tipo_contenido") in prioridad_tipos else 99
        )

        for c in todos_restantes_ordenados:
            costo = _estimar_tokens(c.page_content)
            if costo <= presupuesto_restante:
                cid = c.metadata.get("chunk_id") or c.page_content
                seleccionados_set.add(cid)
                presupuesto_restante -= costo

        # Preservar siempre el orden secuencial del documento original
        chunks_seleccionados = [
            c for c in chunks
            if (c.metadata.get("chunk_id") or c.page_content) in seleccionados_set
        ]

    # Formatear la lista de fragmentos resultante con etiquetas F1...Fn
    resultado = []
    for i, c in enumerate(chunks_seleccionados, start=1):
        meta = c.metadata or {}
        chunk_id = str(meta.get("chunk_id") or f"chk-{i:04d}")
        page = meta.get("page")
        page_end = meta.get("page_end") or page
        section = meta.get("section") or ""
        tipo = meta.get("tipo_contenido") or "afirmacion"

        resultado.append({
            "id": f"F{i}",
            "chunk_id": chunk_id,
            "page": page,
            "page_end": page_end,
            "section": section,
            "tipo_contenido": tipo,
            "contenido": c.page_content,
            "metadatos": meta
        })

    return resultado


def formatear_texto_fuente_etiquetado(fragmentos: List[Dict[str, Any]]) -> str:
    """
    Construye el texto de entrada para el Agente Creador y el Agente Crítico,
    etiquetando cada fragmento con su identificador [F#], páginas y sección.
    """
    if not fragmentos:
        return ""

    bloques = []
    for f in fragmentos:
        fid = f.get("id", "F?")
        chunk_id = f.get("chunk_id", "")
        p_ini = f.get("page")
        p_fin = f.get("page_end")
        pag_str = f"págs. {p_ini}–{p_fin}" if (p_ini and p_fin and p_ini != p_fin) else (f"pág. {p_ini}" if p_ini else "")
        sec = f.get("section")
        sec_str = f"Sección: {sec}" if sec else ""

        etiquetas = [p for p in [fid, chunk_id, pag_str, sec_str] if p]
        header = f"[{' | '.join(etiquetas)}]"
        bloques.append(f"{header}\n{f.get('contenido', '').strip()}")

    return "\n\n---\n\n".join(bloques)
