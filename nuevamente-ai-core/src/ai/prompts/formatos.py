"""
Instrucciones especializadas y plantillas Few-Shot según el formato didáctico solicitado.
Las cantidades son máximos: exigir un mínimo empuja al modelo a rellenar con hechos
que el documento no sustenta.
"""

from src.ai.schemas import FormatoSalidaEnum

INSTRUCCIONES_FORMATOS = {
    FormatoSalidaEnum.FLASHCARDS: (
        "FORMATO SOLICITADO: FLASHCARDS INTERACTIVAS (Tarjetas de Memorización Activa).\n"
        "Genera hasta 8 tarjetas estructuradas: solo tantas como conceptos distintos sustente el texto fuente. "
        "Si el documento es breve, es preferible una tarjeta fiel a varias con relleno.\n"
        "Para cada tarjeta incluye:\n"
        "- frente: Pregunta directa o concepto nuclear.\n"
        "- dorso: Explicación pedagógica clara y rigurosa basada en el texto.\n"
        "- pista_didactica: Analogía o truco mnemotécnico para facilitar la retención, sin datos técnicos nuevos. "
        "Omítela si no hay una analogía que respete esa regla.\n"
        "- categoria_dificultad: 'Básico', 'Intermedio' o 'Avanzado'."
    ),
    FormatoSalidaEnum.QUIZ_INTERACTIVO: (
        "FORMATO SOLICITADO: QUIZ INTERACTIVO DE EVALUACIÓN.\n"
        "Genera hasta 5 preguntas de opción múltiple estructuradas: solo tantas como afirmaciones verificables "
        "contenga el texto fuente.\n"
        "Para cada pregunta incluye:\n"
        "- pregunta: Planteamiento del escenario o pregunta conceptual.\n"
        "- opciones: Exactamente 4 opciones (lista de strings).\n"
        "- indice_correcto: Entero de 0 a 3 indicando la respuesta correcta.\n"
        "- justificacion_tecnica: Explicación exhaustiva del porqué es la opción válida, basada en el texto.\n"
        "- explicacion_distractores: Análisis de por qué cada una de las otras 3 opciones es inválida.\n"
        "- pista_didactica: Pista orientadora sin revelar directamente la respuesta."
    ),
    FormatoSalidaEnum.GUIA_PASO_A_PASO: (
        "FORMATO SOLICITADO: GUÍA PASO A PASO (TUTORIAL PRÁCTICO).\n"
        "Incluye prerrequisitos, lista numerada de pasos con instrucciones detalladas, "
        "bloques de comandos/código cuando aplique y comprobaciones de éxito. "
        "Usa solo pasos, comandos y comprobaciones que aparezcan en el documento."
    ),
    FormatoSalidaEnum.RESUMEN_EJECUTIVO: (
        "FORMATO SOLICITADO: RESUMEN EJECUTIVO (TL;DR ESTRATÉGICO).\n"
        "Incluye un resumen en un párrafo, puntos clave de alto impacto, análisis de impacto en el negocio "
        "y recomendaciones de implementación. Todo debe derivarse del documento: si la fuente no "
        "describe impacto de negocio, indica en 'impacto_negocio' que el documento no lo especifica; "
        "si no contiene recomendaciones, deja 'recomendaciones' como lista vacía."
    )
}


def obtener_instrucciones_formato(formato: str) -> str:
    """Retorna las directrices específicas de salida para el formato seleccionado."""
    try:
        enum_val = FormatoSalidaEnum(formato)
        return INSTRUCCIONES_FORMATOS[enum_val]
    except Exception:
        return INSTRUCCIONES_FORMATOS[FormatoSalidaEnum.FLASHCARDS]
