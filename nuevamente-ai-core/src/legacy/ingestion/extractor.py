"""
Extractor de documentos técnicos para NuevaMente AI Core.
Soporta archivos .pdf (vía PyMuPDF), .md y .txt con extracción estructurada por páginas/secciones.
"""

import os
from typing import Any, Dict, List, Optional


class DocumentExtractor:
    """Clase utilitaria para extraer texto limpio y metadatos de documentos técnicos."""

    @staticmethod
    def extraer_desde_archivo(ruta_archivo: str) -> List[Dict[str, Any]]:
        """
        Extrae el contenido de un archivo local.
        Retorna una lista de diccionarios con:
        - "pagina": int
        - "texto": str
        - "fuente": str
        - "metadatos": dict
        """
        if not os.path.exists(ruta_archivo):
            raise FileNotFoundError(f"El archivo no existe: {ruta_archivo}")

        extension = os.path.splitext(ruta_archivo)[1].lower()
        nombre_base = os.path.basename(ruta_archivo)

        if extension == ".pdf":
            return DocumentExtractor._extraer_pdf(ruta_archivo, nombre_base)
        elif extension in [".md", ".markdown"]:
            return DocumentExtractor._extraer_texto_plano(ruta_archivo, nombre_base, tipo="markdown")
        elif extension == ".txt":
            return DocumentExtractor._extraer_texto_plano(ruta_archivo, nombre_base, tipo="text")
        else:
            raise ValueError(f"Extensión no soportada: {extension}. Use .pdf, .md o .txt")

    @staticmethod
    def _extraer_pdf(ruta_archivo: str, nombre_base: str) -> List[Dict[str, Any]]:
        """Extrae texto de un archivo PDF usando PyMuPDF (fitz)."""
        import fitz  # PyMuPDF

        paginas = []
        doc = fitz.open(ruta_archivo)
        try:
            for num_pag in range(len(doc)):
                pagina = doc.load_page(num_pag)
                texto = pagina.get_text("text").strip()
                if texto:
                    paginas.append({
                        "pagina": num_pag + 1,
                        "texto": texto,
                        "fuente": nombre_base,
                        "metadatos": {
                            "total_paginas": len(doc),
                            "formato": "pdf"
                        }
                    })
        finally:
            doc.close()

        return paginas

    @staticmethod
    def _extraer_texto_plano(ruta_archivo: str, nombre_base: str, tipo: str) -> List[Dict[str, Any]]:
        """Extrae texto de archivos .md o .txt."""
        with open(ruta_archivo, "r", encoding="utf-8", errors="replace") as f:
            contenido = f.read().strip()

        return [{
            "pagina": 1,
            "texto": contenido,
            "fuente": nombre_base,
            "metadatos": {
                "total_paginas": 1,
                "formato": tipo
            }
        }]

    @staticmethod
    def extraer_desde_texto(texto: str, titulo: str = "documento_en_memoria") -> List[Dict[str, Any]]:
        """Permite procesar texto recibido directamente como string (e.g. desde API REST)."""
        return [{
            "pagina": 1,
            "texto": texto.strip(),
            "fuente": titulo,
            "metadatos": {
                "total_paginas": 1,
                "formato": "raw_text"
            }
        }]
