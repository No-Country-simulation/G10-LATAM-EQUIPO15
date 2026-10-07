"""
Punto de entrada público del pipeline de IA para NuevaMente.
Orquesta Ingesta -> Segmentación -> Vector Store -> LangGraph -> Auditoría -> Paquete Validado.
"""

import asyncio
import inspect
import logging
from typing import Any, Dict, Optional, Tuple

from src.ai.graph import grafo_adaptacion_compilado
from src.ai.schemas import AdaptacionContenidoResponse, FormatoSalidaEnum
from src.ai.agents.critico import obtener_umbral

logger = logging.getLogger(__name__)

TOP_K_FRAGMENTOS = 15


class ContextoInsuficienteError(ValueError):
    """El contenido generado no supera el umbral de fidelidad (mapear a HTTP 422 en Backend)."""


class ContenidoInseguroError(ValueError):
    """La auditoría determinista detectó contenido inseguro o estructura rota (mapear a HTTP 422/500)."""


def _construir_query_pedagogica(titulo: str, formato: str) -> str:
    """Traduce el formato pedagógico solicitado en un vector de búsqueda optimizado para RAG."""
    fmt = formato.lower()
    if "flashcards" in fmt:
        return f"Definiciones, conceptos clave, glosario y terminología de {titulo}"
    elif "quiz" in fmt:
        return f"Afirmaciones verificables, datos técnicos, buenas prácticas y reglas de {titulo}"
    elif "guia" in fmt or "tutorial" in fmt:
        return f"Ejemplos prácticos, instrucciones paso a paso, fundamentos y aplicación de {titulo}"
    elif "resumen" in fmt or "tldr" in fmt:
        return f"Resumen ejecutivo, impacto de negocio, ventajas y visión general de {titulo}"
    return f"Conceptos principales, arquitectura y reglas de {titulo}"


def _preparar_estado_inicial(
    documento_titulo: str,
    documento_contenido: Optional[str],
    ruta_archivo: Optional[str],
    perfil: str,
    formato: str,
    nicho: str,
    nivel_detalle: str,
    emitir,
) -> Dict[str, Any]:
    """Ejecuta Ingesta -> Chunking -> VectorStore -> Recuperación y devuelve el estado inicial del grafo."""
    # Validación temprana del formato (define el esquema de salida).
    try:
        FormatoSalidaEnum(formato)
    except ValueError:
        validos = ", ".join(f.value for f in FormatoSalidaEnum)
        raise ValueError(f"Formato '{formato}' no soportado. Valores válidos: {validos}.")

    if not ruta_archivo:
        if documento_contenido:
            raise ValueError("El pipeline DataIA requiere una ruta de archivo (ruta_archivo) para operar.")
        raise ValueError("Debe proporcionar 'ruta_archivo'.")

    # 1. Extracción
    emitir("EXTRACCION", 1, 20, "Extrayendo y normalizando texto del documento...")
    from src.dataia.ingestion.service import ingest_document
    ingestion_res = ingest_document(ruta_archivo)
    if getattr(ingestion_res, "status", None) != "aprobado":
        raise ValueError(f"Error de Ingestión: {getattr(ingestion_res, 'mensaje', 'Desconocido')}")

    # 2. Chunking e indexación vectorial
    emitir("INDEXACION", 2, 40, "Segmentando fragmentos jerárquicos y calculando embeddings...")
    from src.dataia.chunking.service import process_chunks
    from src.dataia.vectorstore.service import process_vectorstore
    from src.dataia.vectorstore.client import get_vector_store

    chunking_res = process_chunks(ingestion_res)
    if getattr(chunking_res, "status", None) != "aprobado":
        raise ValueError(f"Error de Chunking: {getattr(chunking_res, 'mensaje', 'Desconocido')}")

    vs_res = process_vectorstore(chunking_res)
    if getattr(vs_res, "status", None) != "aprobado":
        raise ValueError(f"Error de VectorStore: {getattr(vs_res, 'mensaje', 'Desconocido')}")

    docs_relevantes = get_vector_store().similarity_search(
        query=_construir_query_pedagogica(documento_titulo, formato),
        k=TOP_K_FRAGMENTOS,
        filter={"document_id": vs_res.document_id}
    )
    if not docs_relevantes:
        raise ContextoInsuficienteError("Contexto Insuficiente (Error 422): no se recuperaron fragmentos del documento.")

    # Deduplicar y reordenar por posición en el documento para preservar la coherencia narrativa.
    vistos = set()
    fragmentos_relevantes = []
    for d in sorted(docs_relevantes, key=lambda d: str(d.metadata.get("chunk_id", ""))):
        clave = d.metadata.get("chunk_id") or d.page_content
        if clave in vistos:
            continue
        vistos.add(clave)
        # Clave 'contenido': es la que leen analizador, creador y crítico.
        fragmentos_relevantes.append({"contenido": d.page_content, "metadatos": d.metadata})

    meta_pedagogica = getattr(ingestion_res, "pedagogical_metadata", None)
    conceptos_ingesta = list(getattr(meta_pedagogica, "conceptos_clave", None) or [])

    return {
        "documento_titulo": documento_titulo,
        "documento_contenido": "\n---\n".join(f["contenido"] for f in fragmentos_relevantes),
        "perfil_destinatario": perfil,
        "formato_salida": formato,
        "nicho_sector": nicho,
        "nivel_detalle": nivel_detalle,
        "fragmentos_relevantes": fragmentos_relevantes,
        "conceptos_clave": conceptos_ingesta,
        "prompt_sistema_calibrado": "",
        "tiempo_estimado_minutos": 5,
        "borrador_contenido": None,
        "codigo_mermaid": None,
        "anclaje_fuente_score": 0.0,
        "critica_observaciones": None,
        "contador_intentos": 0,
        "paquete_final_json": None,
        "status": "iniciando",
        "error": None
    }


def _validar_fidelidad(estado_final: Dict[str, Any], formato: str) -> Tuple[float, Dict[str, Any]]:
    """Aplica el umbral de fidelidad (fail-closed) y devuelve (score, paquete_json)."""
    score = float(estado_final.get("anclaje_fuente_score") or 0.0)
    umbral = obtener_umbral(formato)
    if score < umbral:
        raise ContextoInsuficienteError(
            f"Contexto Insuficiente (Error 422): el contenido generado no está suficientemente anclado "
            f"al documento (Score: {score} vs Umbral {umbral}). Detalle: {estado_final.get('critica_observaciones')}"
        )

    paquete_json = estado_final.get("paquete_final_json")
    if not paquete_json:
        raise RuntimeError("El grafo finalizó sin producir un paquete JSON válido.")
    return score, paquete_json


def _aplicar_auditoria(resultado_auditoria) -> bool:
    is_secure, vulns, recs = resultado_auditoria
    if not is_secure:
        logger.warning("Auditoría detectó problemas: %s. Recomendaciones: %s", vulns, recs)
        raise ContenidoInseguroError(f"Auditoría de seguridad rechazó el contenido: {vulns}")
    return is_secure


def ejecutar_pipeline_adaptacion(
    documento_titulo: str,
    documento_contenido: Optional[str] = None,
    ruta_archivo: Optional[str] = None,
    perfil: str = "Junior",
    formato: str = "Flashcards",
    nicho: str = "General",
    nivel_detalle: str = "Didactico",
    callback_telemetria: Optional[Any] = None
) -> AdaptacionContenidoResponse:
    """
    Ejecuta el ciclo integral de adaptación pedagógica (versión síncrona, para scripts/CLI).
    En FastAPI usar `ejecutar_pipeline_adaptacion_async`.
    """
    def emitir(etapa, paso, progreso, mensaje):
        if callback_telemetria:
            callback_telemetria(etapa, paso, progreso, mensaje)

    estado_inicial = _preparar_estado_inicial(
        documento_titulo, documento_contenido, ruta_archivo, perfil, formato, nicho, nivel_detalle, emitir
    )

    emitir("GENERACION", 3, 60, f"LangGraph generando contenido para perfil '{perfil}'...")
    estado_final = grafo_adaptacion_compilado.invoke(estado_inicial)

    score, paquete_json = _validar_fidelidad(estado_final, formato)
    emitir("AUDITORIA", 4, 80, f"Agente Crítico: Fidelidad evaluada ({score}). Iniciando auditoría heurística...")

    from src.ai.agents.auditor import AuditorAgent
    _aplicar_auditoria(asyncio.run(AuditorAgent().auditar_seguridad_async(paquete_json)))

    emitir("COMPLETADO", 5, 100, "Contenido generado y auditado.")
    return AdaptacionContenidoResponse(**paquete_json)


async def _invocar_callback_async(callback: Optional[Any], etapa: str, paso: int, progreso: int, mensaje: str) -> None:
    """Invoca el callback de telemetría soportando tanto funciones síncronas como asíncronas."""
    if not callback:
        return
    if inspect.iscoroutinefunction(callback):
        await callback(etapa, paso, progreso, mensaje)
    else:
        callback(etapa, paso, progreso, mensaje)


async def ejecutar_pipeline_adaptacion_async(
    documento_titulo: str,
    documento_contenido: Optional[str] = None,
    ruta_archivo: Optional[str] = None,
    perfil: str = "Junior",
    formato: str = "Flashcards",
    nicho: str = "General",
    nivel_detalle: str = "Didactico",
    callback_telemetria: Optional[Any] = None
) -> AdaptacionContenidoResponse:
    """
    Versión asíncrona para consumo no bloqueante en endpoints de FastAPI.
    La fase DataIA (bloqueante: PyMuPDF + embeddings) se ejecuta en un hilo; el grafo usa .ainvoke().
    """
    loop = asyncio.get_running_loop()

    def emitir_desde_hilo(etapa, paso, progreso, mensaje):
        """Reenvía la telemetría al event loop en tiempo real desde el hilo de DataIA."""
        if not callback_telemetria:
            return
        if inspect.iscoroutinefunction(callback_telemetria):
            asyncio.run_coroutine_threadsafe(
                callback_telemetria(etapa, paso, progreso, mensaje), loop
            ).result(timeout=10)
        else:
            loop.call_soon_threadsafe(callback_telemetria, etapa, paso, progreso, mensaje)

    estado_inicial = await asyncio.to_thread(
        _preparar_estado_inicial,
        documento_titulo, documento_contenido, ruta_archivo, perfil, formato, nicho, nivel_detalle, emitir_desde_hilo
    )

    await _invocar_callback_async(callback_telemetria, "GENERACION", 3, 60, f"LangGraph generando contenido para perfil '{perfil}'...")
    estado_final = await grafo_adaptacion_compilado.ainvoke(estado_inicial)

    score, paquete_json = _validar_fidelidad(estado_final, formato)
    await _invocar_callback_async(callback_telemetria, "AUDITORIA", 4, 80, f"Agente Crítico: Fidelidad evaluada ({score}). Iniciando auditoría heurística...")

    from src.ai.agents.auditor import AuditorAgent
    _aplicar_auditoria(await AuditorAgent().auditar_seguridad_async(paquete_json))

    await _invocar_callback_async(callback_telemetria, "COMPLETADO", 5, 100, "Contenido generado y auditado.")
    return AdaptacionContenidoResponse(**paquete_json)
