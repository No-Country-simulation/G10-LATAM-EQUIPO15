def validate_content_not_empty(text: str) -> bool:
    """
    Valida que el contenido extraído tenga una longitud razonable y no esté vacío.
    La pertinencia del documento la decide el enriquecimiento pedagógico
    (`apto_para_aprendizaje`), válido para cualquier sector e idioma.
    """
    if not text or len(text.strip()) < 50:
        return False
    return True
