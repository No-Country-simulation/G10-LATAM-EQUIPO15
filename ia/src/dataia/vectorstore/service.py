from dataia.common.models import ChunkingResult, VectorStoreResponse, VectorStoreResult, VectorStoreError
from dataia.vectorstore.client import (
    COLLECTION_NAME, chunk_records, embeddings_enabled, insert_chunks, load_document_record, save_document_record,
)
import os
from dataia.common.providers import is_provider_error

def process_vectorstore(chunking_result: ChunkingResult) -> VectorStoreResponse:
    """
    Orquestador de IA-04:
    Persiste los fragmentos y la metadata pedagógica en el registro del documento,
    que es lo que lee la etapa de generación. Con DATAIA_EMBEDDINGS_ENABLED=true
    también genera embeddings con Gemini y los indexa en ChromaDB.
    """
    try:
        if not chunking_result.chunks:
            return VectorStoreError(
                codigo="SIN_CHUNKS",
                mensaje="El resultado de chunking no contiene fragmentos para procesar."
            )

        if embeddings_enabled():
            # Genera embeddings y persiste manteniendo los metadatos de los chunks
            already_indexed = insert_chunks(chunking_result.chunks)
        else:
            previous = load_document_record(chunking_result.document_id)
            already_indexed = bool(previous) and previous.get("chunk_records") == chunk_records(chunking_result.chunks)
        save_document_record(
            chunking_result.document_id,
            chunking_result.chunks,
            chunking_result.pedagogical_metadata,
        )

        return VectorStoreResult(
            document_id=chunking_result.document_id,
            chunks_inserted=len(chunking_result.chunks),
            collection_name=COLLECTION_NAME,
            already_indexed=already_indexed
        )

    except Exception as e:
        if os.getenv("IA_STRICT_PROVIDERS") == "1" and is_provider_error(e):
            raise
        return VectorStoreError(
            codigo="ERROR_VECTORSTORE",
            mensaje=f"Fallo críto en almacenamiento/embeddings vectorial: {str(e)}"
        )
