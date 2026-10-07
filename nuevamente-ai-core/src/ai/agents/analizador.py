"""
Nodo 1: Analizador e Instruccional (Router & Analyzer).
Extrae los conceptos clave, calibra el prompt de sistema para el perfil y estima el tiempo de estudio.
"""

from typing import Any, Dict
from src.ai.state import EstadoPipelineAdaptacion
from src.ai.prompts.perfiles import obtener_prompt_sistema
from src.ai.prompts.formatos import obtener_instrucciones_formato


def nodo_analizador(state: EstadoPipelineAdaptacion) -> Dict[str, Any]:
    """
    Analiza los parámetros de entrada y los fragmentos contextuales para preparar la estrategia pedagógica.
    """
    perfil = state.get("perfil_destinatario", "Junior")
    formato = state.get("formato_salida", "Flashcards")
    titulo = state.get("documento_titulo", "Documento Técnico")
    fragmentos = state.get("fragmentos_relevantes", [])

    # Obtener prompt de sistema adaptado al perfil
    prompt_sistema = obtener_prompt_sistema(perfil)
    instrucciones_formato = obtener_instrucciones_formato(formato)

    prompt_combinado = f"{prompt_sistema}\n\n{instrucciones_formato}"

    # Conceptos clave: se priorizan los extraídos por DataIA (metadata pedagógica) si vienen en el estado.
    conceptos_unicos = [c for c in (state.get("conceptos_clave") or []) if c and c.strip()][:8]

    if not conceptos_unicos:
        # Respaldo heurístico: términos que aparecen capitalizados en mitad de frase (siglas / nombres propios).
        texto_total = " ".join([f.get("contenido", "") for f in fragmentos]) or state.get("documento_contenido", "")
        import re
        candidatos = re.findall(r"(?<=[a-záéíóúñ,;:]\s)([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚáéíóúñ\-]{2,})", texto_total)
        candidatos += re.findall(r"\b[A-Z]{2,6}\b", texto_total)  # siglas: JWT, OCI, VCN...
        conceptos_unicos = list(dict.fromkeys(candidatos))[:6] or [titulo]

    return {
        "prompt_sistema_calibrado": prompt_combinado,
        "conceptos_clave": conceptos_unicos,
        "contador_intentos": 0,
        "status": "analisis_completado"
    }
