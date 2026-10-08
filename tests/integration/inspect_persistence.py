"""Lee índices y hashes del volumen de ensayo sin invocar proveedores."""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import chromadb

document_id = sys.argv[1]
if not re.fullmatch(r"doc-[a-f0-9]{16}", document_id):
    raise ValueError("document_id inválido")
if os.environ.get("IA_STRICT_PROVIDERS") != "1" or os.environ.get("LLM_PROVIDER") != "gemini":
    raise RuntimeError("La prueba requiere Gemini en modo estricto.")
if not os.environ.get("GOOGLE_API_KEY") or not os.environ.get("GEMINI_API_KEY"):
    raise RuntimeError("Faltan credenciales del proveedor.")
if os.environ.get("GROQ_API_KEY"):
    raise RuntimeError("Este ensayo no admite un proveedor alternativo.")

client = chromadb.PersistentClient(path=os.environ["CHROMADB_DIR"])
collection_name = os.environ.get("CHROMADB_COLLECTION", "nuevamente_docs")
chunk_ids = []
for collection in client.list_collections():
    if collection.name == collection_name:
        chunk_ids = sorted(collection.get(where={"document_id": document_id}, include=["metadatas"])["ids"])
record = Path(os.environ["DATAIA_DOCUMENTS_DIR"]) / f"{document_id}.json"
cache = Path(os.environ["DATAIA_CACHE_DIR"])
cache_hashes = {
    path.relative_to(cache).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted(cache.rglob("*.json"))
}
print(json.dumps({
    "document_id": document_id, "model": os.environ.get("GEMINI_MODEL"),
    "vectors": len(chunk_ids), "chunk_ids": chunk_ids,
    "document_record": record.exists(),
    "document_record_sha256": hashlib.sha256(record.read_bytes()).hexdigest() if record.exists() else None,
    "document_cache": (cache / "metadata" / f"{document_id}.json").exists(),
    "cache_hashes": cache_hashes,
}, sort_keys=True))
