import os
import json
from typing import Optional
from dataia.common.credentials import get_google_api_key
from dataia.common.models import DocumentPedagogicalMetadata
from dataia.common.providers import create_gemini_llm, gemini_fallback_models, provider_call, with_fallback_chain

# El document_id deriva del contenido, por lo que la caché es reutilizable entre ingestiones
CACHE_DIR = os.path.join(os.getenv("DATAIA_CACHE_DIR", ".dataia_cache"), "metadata")
# Conceptos, prerrequisitos y resumen se obtienen de una muestra repartida por todo el documento.
# Enviar un libro completo (~450.000 tokens) en una llamada superó el límite de tokens por minuto (429).
MAX_CHARS = int(os.getenv("DATAIA_ENRICH_MAX_CHARS", "120000"))
VENTANAS_MUESTRA = 12
SEPARADOR_MUESTRA = "\n\n[...]\n\n"


def _muestra_representativa(texto: str, max_chars: Optional[int] = None, ventanas: int = VENTANAS_MUESTRA) -> str:
    """Devuelve el texto completo si cabe; si no, `ventanas` tramos equidistantes de principio a fin."""
    max_chars = MAX_CHARS if max_chars is None else max_chars
    if len(texto) <= max_chars:
        return texto
    tamano = max_chars // ventanas
    paso = (len(texto) - tamano) / (ventanas - 1)
    return SEPARADOR_MUESTRA.join(texto[int(i * paso):int(i * paso) + tamano] for i in range(ventanas))

def enrich_document_metadata(document_id: str, full_text: str) -> DocumentPedagogicalMetadata:
    """
    Generates pedagogical metadata using the configured Gemini model.
    Caches the result in `.dataia_cache/metadata/{document_id}.json`.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{document_id}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return DocumentPedagogicalMetadata(**data)
        except Exception:
            pass # Fallback to re-generating

    try:
        # Solo respaldos Gemini: la entrada (hasta DATAIA_ENRICH_MAX_CHARS) supera el límite gratuito de Groq.
        llm = with_fallback_chain(create_gemini_llm(api_key=get_google_api_key()), [
            create_gemini_llm(api_key=get_google_api_key(), model=m) for m in gemini_fallback_models()
        ])
        structured_llm = llm.with_structured_output(DocumentPedagogicalMetadata)
        
        texto = _muestra_representativa(full_text)
        aviso_muestra = (
            "El documento es extenso: se incluyen tramos distribuidos de principio a fin, separados por [...].\n"
            if texto is not full_text else ""
        )
        prompt = (
            "Extrae la metadata pedagógica del siguiente documento. Puede pertenecer a cualquier sector "
            "(tecnología, finanzas, salud, marketing, negocios, etc.) y estar en cualquier idioma. "
            "Indica en 'apto_para_aprendizaje' si contiene conocimiento del que se pueda generar material de estudio.\n"
            f"{aviso_muestra}"
            f"El ID del documento es: {document_id}\n\n"
            f"Documento:\n{texto}\n"
        )
        
        with provider_call("ENRIQUECIMIENTO_DOCUMENTO"):
            result = structured_llm.invoke(prompt)
        
        # Ensure document_id is correct
        result.document_id = document_id
        
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
            
        return result
    except Exception as e:
        if os.getenv("IA_STRICT_PROVIDERS") == "1":
            raise
        return DocumentPedagogicalMetadata(
            document_id=document_id,
            conceptos_clave=[],
            prerequisitos=[],
            resumen_ejecutivo="No se pudo extraer el resumen.",
            nicho_sugerido="General"
        )
