"""
Servicio de Vector Store (ChromaDB) para búsqueda semántica de fragmentos técnicos.
"""

import os
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings


class VectorStoreService:
    """Gestiona colecciones en ChromaDB para almacenamiento y consulta de fragmentos."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        # Cliente persistente local
        self.client = chromadb.PersistentClient(path=self.persist_dir)

    @staticmethod
    def _limpiar_nombre(nombre: str) -> str:
        limpio = "".join(c if c.isalnum() or c in "-_" else "_" for c in nombre)
        limpio = limpio.strip("_.-")
        if len(limpio) < 3:
            limpio = f"doc_{limpio}".strip("_.-")
        limpio = limpio[:63].strip("_.-")
        return limpio if len(limpio) >= 3 else "documento_tecnico"

    def indexar_documento(
        self,
        coleccion_nombre: str,
        fragmentos: List[Dict[str, Any]]
    ) -> int:
        """
        Indexa los fragmentos en una colección de ChromaDB (utiliza la función de embeddings interna por defecto).
        """
        nombre_limpio = self._limpiar_nombre(coleccion_nombre)
        coleccion = self.client.get_or_create_collection(name=nombre_limpio)

        ids = [f["chunk_id"] for f in fragmentos]
        documents = [f["contenido"] for f in fragmentos]
        metadatas = [{"pagina": f["pagina"], "fuente": f["fuente"], "indice": f["indice"]} for f in fragmentos]

        if ids:
            coleccion.upsert(ids=ids, documents=documents, metadatas=metadatas)

        return len(ids)

    def buscar_similares(
        self,
        coleccion_nombre: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recupera los fragmentos más afines semánticamente a la consulta.
        """
        nombre_limpio = self._limpiar_nombre(coleccion_nombre)
        try:
            coleccion = self.client.get_collection(name=nombre_limpio)
        except Exception:
            return []

        conteo = coleccion.count()
        if conteo == 0:
            return []

        n_results = min(top_k, conteo)
        resultados = coleccion.query(query_texts=[query], n_results=n_results)

        fragmentos_recuperados = []
        docs = resultados.get("documents", [[]])[0]
        metas = resultados.get("metadatas", [[]])[0]
        distances = resultados.get("distances", [[]])[0] if "distances" in resultados else []

        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            dist = distances[i] if i < len(distances) else 0.0
            fragmentos_recuperados.append({
                "contenido": doc,
                "pagina": meta.get("pagina", 1),
                "fuente": meta.get("fuente", ""),
                "distancia": dist
            })

        return fragmentos_recuperados
