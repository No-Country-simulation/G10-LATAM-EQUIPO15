import os
from typing import Optional

def get_google_api_key() -> Optional[str]:
    """
    Clave de Gemini para los módulos Data/IA (ingestión, chunking y vector store).
    DATAIA_GOOGLE_API_KEY permite que estas etapas consuman una cuota propia,
    separada de la que usa AI Core; si no está definida, se usa GOOGLE_API_KEY.
    """
    return os.getenv("DATAIA_GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") or None
