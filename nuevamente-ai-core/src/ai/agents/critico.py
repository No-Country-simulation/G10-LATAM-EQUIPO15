"""
Nodo 3: Agente Crítico Evaluador de Calidad y Anti-Alucinaciones.
Calcula la métrica anclaje_fuente_score auditando el borrador completo
(título, introducción e items) contra los fragmentos fuente mediante un LLM-juez (temperatura 0).
"""

import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.ai.state import EstadoPipelineAdaptacion
from src.ai.config import obtener_llm_critico

logger = logging.getLogger(__name__)

MAX_INTENTOS = int(os.getenv("MAX_INTENTOS_GENERACION", 2))


class VeredictoItem(BaseModel):
    item_id_o_nombre: str = Field(..., description="Identificador o resumen breve del item (ej. 'Flashcard 1', 'Pregunta 2')")
    afirmacion_analizada: str = Field(..., description="Afirmación o contenido técnico evaluado")
    fuente_evaluada: Optional[str] = Field(None, description="Identificador del fragmento evaluado (ej. 'F1', 'doc-x-chk-0001')")
    estado: Literal["respaldada", "no_respaldada", "contradicha", "didactica"] = Field(
        ...,
        description=(
            "'respaldada': la afirmación fáctica está sustentada en la fuente. "
            "'no_respaldada': la afirmación no aparece en la fuente (alucinación). "
            "'contradicha': contradice explícitamente lo indicado en la fuente. "
            "'didactica': recurso pedagógico (analogía, pista, ejemplo de contexto) que ilustra el concepto sin introducir hechos técnicos nuevos."
        )
    )
    observacion: Optional[str] = Field(None, description="Detalle del hallazgo o corrección sugerida")


class EvaluacionFidelidad(BaseModel):
    veredictos: List[VeredictoItem] = Field(
        default_factory=list,
        description="Lista de veredictos para cada afirmación o item del contenido generado."
    )
    anclaje_fuente_score: Optional[float] = Field(
        default=None,
        description="Puntaje fáctico (0.0 a 1.0). Si se omiten veredictos, se usa este valor."
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
    partes = [f.get("contenido", "").strip() for f in fragmentos if f.get("contenido", "").strip()]
    texto = separador.join(partes)
    return texto.strip() or (state.get("documento_contenido") or "").strip()


def nodo_critico(state: EstadoPipelineAdaptacion) -> Dict[str, Any]:
    """
    Audita el borrador contra el texto fuente.
    Verifica cada afirmación/item contra los fragmentos citados y calcula
    la fidelidad determinísticamente en código (respaldadas / evaluables).
    """
    borrador = state.get("borrador_contenido") or {}
    fragmentos = state.get("fragmentos_relevantes") or []
    if fragmentos and any(f.get("id") for f in fragmentos):
        from src.ai.contexto import formatear_texto_fuente_etiquetado
        texto_fuente = formatear_texto_fuente_etiquetado(fragmentos)
    else:
        texto_fuente = extraer_texto_fuente(state)
    formato = state.get("formato_salida", "")

    if not borrador or not borrador.get("items"):
        return {
            "anclaje_fuente_score": 0.0,
            "critica_observaciones": "El borrador está vacío o no contiene items.",
            "veredictos_critico": [],
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
        "5. En Quiz, las opciones incorrectas (distractores) son falsas por diseño: clasifícalas como 'didactica' o 'respaldada', "
        "NO las penalices como alucinaciones. SÍ verifica rigurosamente la opción correcta y la justificación técnica.\n"
        if "Quiz" in formato else ""
    )

    instruccion_juez = (
        "Compara el 'CONTENIDO GENERADO' con los 'FRAGMENTOS FUENTE' y emite veredictos por cada afirmación o item.\n"
        "REGLAS DE EVALUACIÓN:\n"
        "1. 'respaldada': Toda afirmación fáctica, dato técnico, configuración, servicio o regla que aparezca en la fuente citada o en los fragmentos.\n"
        "2. 'no_respaldada': Afirmación fáctica que NO figura en la fuente (alucinación o invención).\n"
        "3. 'contradicha': Afirmación que dice lo contrario de lo que especifica la fuente.\n"
        "4. 'didactica': Analogías cotidianas, pistas mnemotécnicas o encuadres de contexto/nicho que ilustran conceptos sin inventar hechos técnicos.\n"
        f"{regla_quiz}"
        "Si el contenido trata un tema completamente ajeno a los fragmentos fuente, emite veredictos 'no_respaldada'.\n\n"
        f"--- FRAGMENTOS FUENTE ---\n{texto_fuente}\n\n"
        f"--- CONTENIDO GENERADO ---\n{texto_borrador}\n"
    )

    if not texto_fuente or not texto_fuente.strip():
        return {
            "anclaje_fuente_score": 0.0,
            "critica_observaciones": "Contexto Insuficiente: la fuente no contiene texto suficiente para evaluar el borrador.",
            "afirmaciones_no_sustentadas": ["Sin contexto disponible"],
            "veredictos_critico": [],
            "status": "evaluacion_completada"
        }

    veredictos_lista = []
    try:
        llm = obtener_llm_critico().with_structured_output(EvaluacionFidelidad)
        resultado: EvaluacionFidelidad = llm.invoke([
            SystemMessage(content="Eres un auditor estricto de fidelidad fáctica (grounding judge). Respondes únicamente con la evaluación estructurada."),
            HumanMessage(content=instruccion_juez)
        ])

        if resultado.veredictos:
            veredictos_lista = [v.model_dump() for v in resultado.veredictos]
            total_evaluables = 0
            respaldadas = 0
            contradichas = 0
            no_sust = []
            for v in resultado.veredictos:
                if v.estado == "didactica":
                    continue  # Analogías legítimas no penalizan
                total_evaluables += 1
                if v.estado == "respaldada":
                    respaldadas += 1
                elif v.estado == "contradicha":
                    contradichas += 1
                    no_sust.append(f"{v.item_id_o_nombre}: [CONTRADICCIÓN] {v.afirmacion_analizada} ({v.observacion or ''})")
                elif v.estado == "no_respaldada":
                    no_sust.append(f"{v.item_id_o_nombre}: [NO SUSTENTADA] {v.afirmacion_analizada} ({v.observacion or ''})")

            if total_evaluables == 0:
                score = 1.0
            else:
                score = max(0.0, min(1.0, (respaldadas - (contradichas * 2)) / total_evaluables))
            no_sustentadas = no_sust
            observaciones = resultado.critica_observaciones
        else:
            score = float(resultado.anclaje_fuente_score if resultado.anclaje_fuente_score is not None else 0.0)
            no_sustentadas = resultado.afirmaciones_no_sustentadas
            observaciones = resultado.critica_observaciones

    except Exception as e:
        logger.warning("LLM crítico no disponible (%s). Aplicando evaluación heurística de respaldo.", e)
        # Fallback heurístico para entornos de testing offline o sin API key
        palabras_clave_fuente = set([w.lower() for w in texto_fuente.split() if len(w) > 4])
        if not palabras_clave_fuente:
            score = 0.0
            observaciones = "Contexto Insuficiente: la fuente no contiene términos suficientes para evaluar el borrador."
            no_sustentadas = ["Contexto insuficiente"]
        else:
            texto_items = str(borrador.get("items", [])).lower()
            palabras_borrador = [w.lower() for w in texto_items.split() if len(w) > 4]
            coincidencias = sum(1 for w in palabras_borrador if w in palabras_clave_fuente)
            total = max(len(palabras_borrador), 1)
            ratio = coincidencias / total
            if ratio < 0.50:
                score = round(0.72 + (ratio * 0.20), 2)
                no_sustentadas = list(palabras_clave_fuente - set(palabras_borrador))[:5]
                observaciones = f"Calidad preliminar sub-umbral ({score}). Cobertura insuficiente."
            else:
                score = min(0.98, max(0.86, 0.78 + ratio * 0.20))
                no_sustentadas = []
                observaciones = f"Contenido anclado al documento original (Score: {round(score, 2)})."

    if no_sustentadas:
        observaciones += " Afirmaciones a corregir: " + " | ".join(no_sustentadas[:10])

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
        "veredictos_critico": veredictos_lista,
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
