"""
Módulo de contexto y selección pedagógica para NuevaMente AI Core.
Adapta la lectura de DataIA (Fase A) seleccionando fragmentos según formato
y presupuesto de tokens, con trazabilidad jerárquica (sección, página, tipo).
"""

import logging
import math
import os
from typing import Any, Callable, Dict, List, Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Presupuesto predeterminado de tokens de contexto para la llamada al LLM.
# Configurable: el modelo admite mucho más contexto, a cambio de más latencia y costo.
PRESUPUESTO_TOKENS_DEFAULT = int(os.getenv("IA_CONTEXTO_PRESUPUESTO_TOKENS", "24000"))


def _obtener_cliente_vectorstore():
    """Utiliza la única instancia del paquete Data/IA de la integración."""
    from dataia.vectorstore import client
    return client


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
            logger.warning("Fallo al invocar get_document_chunks: %s. Reintentando vía Chroma directo.", type(e).__name__)

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
            logger.debug("No se pudo cargar el registro de documento desde disco: %s", type(e).__name__)

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
                    "prerequisitos": getattr(ped_obj, "prerequisitos", []),
                    "resumen_ejecutivo": getattr(ped_obj, "resumen_ejecutivo", "")
                }

    conceptos = list((ped_meta or {}).get("conceptos_clave") or [])
    # Data/IA guarda 'prerequisitos' (nombre del modelo y de las cachés existentes);
    # se acepta también 'prerrequisitos' por compatibilidad. AI Core expone 'prerrequisitos'.
    prerrequisitos = list((ped_meta or {}).get("prerequisitos") or (ped_meta or {}).get("prerrequisitos") or [])
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


def _preseleccionar_candidatos(chunks: List[Document], objetivo_tokens: float, tokens_totales: int) -> List[Document]:
    """
    Candidatos repartidos por sección en proporción a su tamaño y espaciados dentro de cada una,
    hasta `objetivo_tokens`. Siempre incluye al menos uno por sección. Conserva el orden del documento.
    """
    por_seccion: Dict[str, List[Document]] = {}
    for c in chunks:
        por_seccion.setdefault(str(c.metadata.get("section") or "General"), []).append(c)
    elegidos = set()
    for items in por_seccion.values():
        tokens_seccion = sum(_estimar_tokens(c.page_content) for c in items)
        cuota = objetivo_tokens * tokens_seccion / tokens_totales
        cantidad = min(len(items), max(1, math.ceil(cuota / (tokens_seccion / len(items)))))
        if cantidad == 1:
            indices = {0}
        else:
            indices = {round(i * (len(items) - 1) / (cantidad - 1)) for i in range(cantidad)}
        elegidos.update(id(items[i]) for i in indices)
    return [c for c in chunks if id(c) in elegidos]


# Candidatos clasificados por cada fragmento que entra en el presupuesto
FACTOR_CANDIDATOS = 2


def seleccionar_fragmentos(
    chunks: List[Document],
    formato: str,
    presupuesto_tokens: int = PRESUPUESTO_TOKENS_DEFAULT,
    clasificar: Optional[Callable[[List[str]], List[str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Selecciona fragmentos respetando el formato didáctico y el presupuesto de tokens:
    - Si el documento completo cabe en el presupuesto, se entrega completo en su orden original.
    - Si supera el presupuesto, prioriza por tipo_contenido y garantiza cobertura por sección.
    `clasificar(textos) -> tipos` asigna tipo_contenido solo a los candidatos (el doble de lo que
    cabe): clasificar cientos de fragmentos para usar unos pocos agotaba el tiempo del pipeline.
    Sin `clasificar`, se usa el tipo_contenido que ya traigan los metadatos.
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
        if clasificar is not None:
            base = _preseleccionar_candidatos(chunks, presupuesto_tokens * FACTOR_CANDIDATOS, tokens_totales)
            tipos = clasificar([c.page_content for c in base])
            base = [
                Document(page_content=c.page_content, metadata={**(c.metadata or {}), "tipo_contenido": tipo})
                for c, tipo in zip(base, tipos)
            ]
        else:
            base = list(chunks)
        tokens_base = sum(_estimar_tokens(c.page_content) for c in base)

        fmt = (formato or "").lower()
        if "flashcard" in fmt:
            prioridad_tipos = ["definicion", "afirmacion", "procedimiento", "ejemplo", "codigo", "tabla"]
        elif "quiz" in fmt:
            prioridad_tipos = ["afirmacion", "procedimiento", "definicion", "ejemplo", "codigo", "tabla"]
        elif "guia" in fmt or "tutorial" in fmt:
            prioridad_tipos = ["procedimiento", "codigo", "ejemplo", "definicion", "afirmacion", "tabla"]
        else:  # Resumen, Mapa Mental, etc.
            prioridad_tipos = ["definicion", "afirmacion", "procedimiento", "ejemplo", "codigo", "tabla"]

        def prioridad(c: Document) -> int:
            tipo = c.metadata.get("tipo_contenido")
            return prioridad_tipos.index(tipo) if tipo in prioridad_tipos else 99

        def clave(c: Document) -> str:
            return c.metadata.get("chunk_id") or c.page_content

        # Agrupar por sección; dentro de cada una, orden por prioridad de tipo
        # (el orden estable conserva la posición en el documento ante empates).
        por_seccion: Dict[str, List[Document]] = {}
        for c in base:
            sec = str(c.metadata.get("section") or "General")
            por_seccion.setdefault(sec, []).append(c)
        candidatos = {sec: sorted(items, key=prioridad) for sec, items in por_seccion.items()}

        seleccionados_set = set()
        presupuesto_restante = presupuesto_tokens
        usado_por_seccion = {sec: 0 for sec in por_seccion}

        def agregar(sec: str, c: Document) -> None:
            nonlocal presupuesto_restante
            costo = _estimar_tokens(c.page_content)
            seleccionados_set.add(clave(c))
            presupuesto_restante -= costo
            usado_por_seccion[sec] += costo

        # Fase A: al menos 1 chunk por sección (cobertura completa del documento).
        # Tiene prioridad sobre el presupuesto: omitir una sección es peor que exceder el límite.
        for sec, items in candidatos.items():
            agregar(sec, items[0])

        # Fase B: cada sección recibe una cuota proporcional a su tamaño en el documento.
        # Antes se llenaba en orden de aparición y las últimas secciones quedaban con un fragmento.
        for sec, items in candidatos.items():
            cuota = presupuesto_tokens * sum(_estimar_tokens(c.page_content) for c in items) / tokens_base
            for c in items:
                costo = _estimar_tokens(c.page_content)
                if clave(c) in seleccionados_set or costo > presupuesto_restante:
                    continue
                if usado_por_seccion[sec] + costo <= cuota:
                    agregar(sec, c)

        # Fase C: el presupuesto sobrante se reparte por turnos entre secciones.
        pendientes = {sec: [c for c in items if clave(c) not in seleccionados_set] for sec, items in candidatos.items()}
        hubo_cambios = True
        while hubo_cambios:
            hubo_cambios = False
            for sec, cola in pendientes.items():
                while cola:
                    c = cola.pop(0)
                    # Un chunk que no cabe ahora no cabrá después: el presupuesto solo disminuye.
                    if _estimar_tokens(c.page_content) <= presupuesto_restante:
                        agregar(sec, c)
                        hubo_cambios = True
                        break

        # Preservar siempre el orden secuencial del documento original
        chunks_seleccionados = [c for c in base if clave(c) in seleccionados_set]

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
