"""
Fábrica agnóstica de LLMs para NuevaMente AI Core.
Gemini es el proveedor principal. Ante un fallo (503 por sobrecarga, 429 por cuota) se
reintenta con los modelos de GEMINI_FALLBACK_MODELS, que tienen cuota propia, y luego
con Groq si GROQ_API_KEY tiene valor.
"""

import os
from typing import Optional
from dataia.common.providers import (
    create_gemini_llm, create_groq_llm, gemini_fallback_models, with_fallback_chain,
)

try:
    # Habilitar caché global en memoria para ahorrar tokens
    from langchain.globals import set_llm_cache
    from langchain_community.cache import InMemoryCache
    set_llm_cache(InMemoryCache())
except ImportError:
    # Silently pass if langchain globals or community packages are missing (Fallback for environments without them)
    pass

# Groq gratuito admite 8.000 tokens por minuto por modelo (medido en los encabezados).
# Cada rol prueba sus modelos en orden: el generador empieza por gpt-oss-20b para dejar la
# cuota de gpt-oss-120b al crítico, que es el juez más riguroso (un veredicto por afirmación).
GROQ_MODEL_DEFAULT = "openai/gpt-oss-20b,openai/gpt-oss-120b"
GROQ_CRITIC_MODEL_DEFAULT = "openai/gpt-oss-120b,openai/gpt-oss-20b"


def _groq_models(critico: bool) -> list[str]:
    valor = os.getenv("GROQ_CRITIC_MODEL", GROQ_CRITIC_MODEL_DEFAULT) if critico else os.getenv("GROQ_MODEL", GROQ_MODEL_DEFAULT)
    return [m.strip() for m in valor.split(",") if m.strip()]


def obtener_llm_adaptacion(temperatura: float = 0.3, provider_override: Optional[str] = None, critico: bool = False):
    """
    Retorna una instancia de LLM lista para invocar, configurada según variables de entorno,
    con la cadena de respaldo Gemini -> Gemini alternativos -> Groq.
    """
    provider = provider_override or os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            raise ValueError("GROQ_API_KEY no encontrada en el entorno.")
        modelos = _groq_models(critico)
        return with_fallback_chain(create_groq_llm(temperatura, modelos[0]), [create_groq_llm(temperatura, m) for m in modelos[1:]])

    # Proveedor primario: Google Gemini
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY no encontrada en el entorno. Configure .env")

    respaldos = [create_gemini_llm(temperatura, model=m) for m in gemini_fallback_models()]
    if os.getenv("GROQ_API_KEY"):
        try:
            respaldos.extend(create_groq_llm(temperatura, m) for m in _groq_models(critico))
        except ImportError:
            pass
    return with_fallback_chain(create_gemini_llm(temperatura), respaldos)


def obtener_llm_critico():
    """Retorna un modelo determinista (temperatura=0.0) para el Agente Crítico de Calidad."""
    return obtener_llm_adaptacion(temperatura=0.0, critico=True)
