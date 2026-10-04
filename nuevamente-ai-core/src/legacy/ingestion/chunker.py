"""
Segmentador semántico contextual (Chunker) para NuevaMente AI Core.
Implementa división jerárquica con preservación de encabezados técnicos y metadatos contextuales.
"""

from typing import Any, Dict, List

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        RecursiveCharacterTextSplitter = None


class DocumentChunker:
    """Divide texto técnico en fragmentos coherentes con solapamiento controlado."""

    def __init__(self, chunk_size: int = 3200, chunk_overlap: int = 600):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        if RecursiveCharacterTextSplitter:
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n## ", "\n### ", "\n#### ", "\n```", "\n\n", "\n", " "],
                length_function=len
            )
        else:
            self.splitter = None

    def _split_fallback(self, texto: str) -> List[str]:
        """División heurística pura en Python si no está instalado langchain_text_splitters."""
        if len(texto) <= self.chunk_size:
            return [texto]
        chunks = []
        start = 0
        while start < len(texto):
            end = start + self.chunk_size
            if end >= len(texto):
                chunks.append(texto[start:].strip())
                break
            # Buscar el último salto de línea en la ventana
            idx = texto.rfind("\n", start + self.chunk_size - self.chunk_overlap, end)
            if idx == -1:
                idx = end
            chunks.append(texto[start:idx].strip())
            start = idx
        return [c for c in chunks if c]

    def segmentar_paginas(self, paginas_extraidas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Toma las páginas extraídas por DocumentExtractor y genera fragmentos enriquecidos con cabecera.
        """
        fragmentos_finales = []
        chunk_idx = 0

        for pag in paginas_extraidas:
            texto_pag = pag.get("texto", "")
            num_pag = pag.get("pagina", 1)
            fuente = pag.get("fuente", "documento")

            if self.splitter:
                sub_chunks = self.splitter.split_text(texto_pag)
            else:
                sub_chunks = self._split_fallback(texto_pag)

            for sc in sub_chunks:
                # Inyección de metadatos de cabecera contextual para el RAG
                cabecera_contextual = f"[Doc: {fuente} | Pág: {num_pag} | Fragmento: {chunk_idx + 1}]\n"
                texto_enriquecido = cabecera_contextual + sc.strip()

                fragmentos_finales.append({
                    "chunk_id": f"{fuente}_p{num_pag}_c{chunk_idx}",
                    "contenido": texto_enriquecido,
                    "texto_puro": sc.strip(),
                    "pagina": num_pag,
                    "fuente": fuente,
                    "indice": chunk_idx
                })
                chunk_idx += 1

        return fragmentos_finales
