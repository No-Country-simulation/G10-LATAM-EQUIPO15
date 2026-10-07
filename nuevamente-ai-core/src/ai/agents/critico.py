"""
Nodo 3: Agente Crítico Evaluador de Calidad y Anti-Alucinaciones.
Calcula la métrica anclaje_fuente_score auditando el borrador completo
(título, introducción e items) contra los fragmentos fuente mediante un LLM-juez (temperatura 0).
"""

import json
import logging
import os
from typing import Any, Dict, List

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.ai.state import EstadoPipelineAdaptacion
from src.ai.config import obtener_llm_critico

logger = logging.getLogger(__name__)

MAX_INTENTOS = int(os.getenv("MAX_INTENTOS_GENERACION", 2))


class EvaluacionFidelidad(BaseModel):
    anclaje_fuente_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Proporción (0.0 a 1.0) de afirmaciones del contenido que están respaldadas por la fuente."
    )
    afirmaciones_no_sustentadas: List[str] = Field(
        default_factory=list,
        description="Lista literal de afirmaciones del contenido generado que NO están respaldadas por la fuente."
    )
    critica_observaciones: str = Field(..., description="Explicación breve y accionable de los hallazgos.")


def obtener_umbral(formato: str) -> float:
    """Umbral único de aprobación (usado por el router del grafo y por el pipeline)."""
    umbral_base = float(os.getenv("UMBRAL_ANCLAJE_MINIMO", 0.85))
    # Menor exigencia en Quiz: los distractores son falsos por diseño.
    return min(umbral_base, 0.75) if "Quiz" in (formato or "") else umbral_base


def extraer_texto_fuente(state: EstadoPipelineAdaptacion, separador: str = "\n---\n") -> str:
    """Obtiene el texto fuente desde los fragmentos recuperados (o el contenido completo como respaldo)."""
    fragmentos = state.get("fragmentos_relevantes") or []
    texto = separador.join(f.get("contenido", "") for f in fragmentos if f.get("contenido"))
    return texto or state.get("documento_contenido", "")


def nodo_critico(state: EstadoPipelineAdaptacion) -> Dict[str, Any]:
    """
    Audita el borrador contra el texto fuente.
    Si el score supera el umbral del formato, el contenido se aprueba;
    si no, y quedan intentos, se solicita auto-corrección con feedback concreto.
    """
    borrador = state.get("borrador_contenido") or {}
    texto_fuente = extraer_texto_fuente(state)
    formato = state.get("formato_salida", "")

    if not borrador or not borrador.get("items"):
        return {
            "anclaje_fuente_score": 0.0,
            "critica_observaciones": "El borrador está vacío o no contiene items.",
            "status": "evaluacion_completada"
        }

    # Se evalúa TODO el contenido visible para el usuario, no solo los items.
    texto_borrador = json.dumps(
        {
            "titulo": borrador.get("titulo"),
            "introduccion_contextualizada": borrador.get("introduccion_contextualizada"),
            "items": borrador.get("items"),
        },
        ensure_ascii=False,
        indent=1,
    )

    regla_quiz = (
        "4. En Quiz, las opciones incorrectas (distractores) son falsas por diseño: NO las penalices, "
        "pero SÍ verifica que la opción marcada como correcta y la justificación estén respaldadas por la fuente.\n"
        if "Quiz" in formato else ""
    )

    instruccion_juez = (
        "Compara el 'CONTENIDO GENERADO' con los 'FRAGMENTOS FUENTE' y detecta alucinaciones.\n"
        "REGLAS:\n"
        "1. Toda afirmación técnica, cifra, nombre de servicio, regla o beneficio debe estar respaldada por la fuente.\n"
        "2. El parafraseo es válido si el significado factual se mantiene intacto.\n"
        "3. Las analogías/pistas didácticas son aceptables SOLO si no introducen hechos técnicos nuevos.\n"
        f"{regla_quiz}"
        "CÁLCULO DEL SCORE: (afirmaciones respaldadas) / (afirmaciones totales). "
        "Si el contenido trata un tema distinto al de la fuente, el score debe ser menor a 0.3.\n"
        "Lista literalmente cada afirmación no sustentada.\n\n"
        f"--- FRAGMENTOS FUENTE ---\n{texto_fuente}\n\n"
        f"--- CONTENIDO GENERADO ---\n{texto_borrador}\n"
    )

    try:
        llm = obtener_llm_critico().with_structured_output(EvaluacionFidelidad)
        resultado: EvaluacionFidelidad = llm.invoke([
            SystemMessage(content="Eres un auditor estricto de fidelidad fáctica (grounding judge). Respondes solo con la evaluación."),
            HumanMessage(content=instruccion_juez)
        ])
        score = float(resultado.anclaje_fuente_score)
        no_sustentadas = resultado.afirmaciones_no_sustentadas
        observaciones = resultado.critica_observaciones
    except Exception as e:
        # Fail-closed: si no se puede evaluar, no se aprueba.
        logger.error("Error en LLM crítico: %s", e)
        score = 0.0
        no_sustentadas = []
        observaciones = f"No fue posible evaluar la fidelidad: {e}"

    if no_sustentadas:
        observaciones += " Afirmaciones a eliminar o corregir: " + " | ".join(no_sustentadas[:10])

    umbral = obtener_umbral(formato)
    intentos = state.get("contador_intentos", 0)
    if score < umbral and intentos < MAX_INTENTOS:
        observaciones = (
            f"Calidad sub-umbral ({score:.2f} < {umbral}). {observaciones} "
            "Reescribe usando únicamente información presente en el texto fuente."
        )
    else:
        observaciones = f"Fidelidad evaluada (Score: {score:.2f}). {observaciones}"

    return {
        "anclaje_fuente_score": round(score, 2),
        "critica_observaciones": observaciones,
        "status": "evaluacion_completada"
    }


def decidir_proximo_paso(state: EstadoPipelineAdaptacion) -> str:
    """Función de enrutamiento condicional para LangGraph."""
    umbral = obtener_umbral(state.get("formato_salida", ""))
    score = state.get("anclaje_fuente_score", 0.0)
    intentos = state.get("contador_intentos", 0)

    if score >= umbral or intentos >= MAX_INTENTOS:
        return "nodo_ensamblador"
    return "nodo_creador"
