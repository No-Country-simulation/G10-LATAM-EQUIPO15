import re
import os
import json
import uuid
import hashlib
import logging
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Literal, NamedTuple, Optional, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dataia.common.credentials import get_google_api_key
from dataia.common.models import ExtractedContent, Chunk, ChunkMetadata
from dataia.common.providers import create_gemini_llm, gemini_fallback_models, provider_call, with_fallback_chain
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# La caché se indexa por el hash del texto del chunk: es válida aunque cambien los ids
CACHE_DIR = os.path.join(os.getenv("DATAIA_CACHE_DIR", ".dataia_cache"), "chunk_metadata")
# Fragmentos clasificados por llamada al LLM
BATCH_SIZE = max(1, int(os.getenv("DATAIA_ENRICH_BATCH_SIZE", "15")))
# Lotes enviados a la vez al proveedor; subirlo acelera, pero consume más cuota por minuto
CONCURRENCY = max(1, int(os.getenv("DATAIA_ENRICH_CONCURRENCY", "4")))
# Sin títulos, los párrafos se agrupan en fragmentos de hasta este tamaño (tokens estimados)
PARAGRAPH_GROUP_TOKENS = int(os.getenv("DATAIA_PARAGRAPH_GROUP_TOKENS", "200"))
# Las páginas se unen como párrafos para que un concepto pueda cruzar de página
PAGE_JOINER = "\n\n"

CODE_PATTERN = re.compile(r"```.*?```", re.DOTALL)
HEADER_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)

TipoContenido = Literal["definicion", "procedimiento", "ejemplo", "afirmacion", "tabla", "codigo"]

class ChunkPedagogicalInfo(BaseModel):
    tipo_contenido: TipoContenido = Field(description="definicion | procedimiento | ejemplo | afirmacion | tabla | codigo")
    nivel_dificultad: int = Field(ge=1, le=5, description="1 al 5")
    concepto_principal: str = Field(description="Concepto principal del chunk")

class ChunkPedagogicalItem(ChunkPedagogicalInfo):
    indice: int = Field(description="Número del fragmento analizado")

class ChunkPedagogicalBatch(BaseModel):
    fragmentos: List[ChunkPedagogicalItem]

def _default_info() -> ChunkPedagogicalInfo:
    return ChunkPedagogicalInfo(tipo_contenido="afirmacion", nivel_dificultad=1, concepto_principal="General")

def _get_llm():
    return with_fallback_chain(create_gemini_llm(api_key=get_google_api_key()), [
        create_gemini_llm(api_key=get_google_api_key(), model=m) for m in gemini_fallback_models()
    ])

def _cache_file(text: str) -> str:
    return os.path.join(CACHE_DIR, f"{hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]}.json")

def _read_cache(text: str) -> Optional[ChunkPedagogicalInfo]:
    cache_file = _cache_file(text)
    if not os.path.exists(cache_file):
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            return ChunkPedagogicalInfo(**json.load(f))
    except Exception:
        return None

def _write_cache(text: str, info: ChunkPedagogicalInfo) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_file(text), "w", encoding="utf-8") as f:
        f.write(info.model_dump_json(indent=2))

def _enrich_batch(texts: List[str]) -> Dict[int, ChunkPedagogicalInfo]:
    """Clasifica varios fragmentos en una sola llamada; devuelve los que el LLM respondió."""
    structured_llm = _get_llm().with_structured_output(ChunkPedagogicalBatch)
    fragmentos = "\n\n".join(f"=== FRAGMENTO {i} ===\n{text}" for i, text in enumerate(texts))
    prompt = (
        "Analiza cada uno de los siguientes fragmentos de un documento técnico. Para cada fragmento devuelve "
        "su número (indice), su tipo de contenido (definicion, procedimiento, ejemplo, afirmacion, tabla o codigo), "
        "su nivel de dificultad (1-5) y su concepto principal. Responde una entrada por fragmento.\n\n"
        f"{fragmentos}\n"
    )
    with provider_call("ENRIQUECIMIENTO_LOTE"):
        result = structured_llm.invoke(prompt)
    if result is None:
        return {}
    return {
        item.indice: ChunkPedagogicalInfo(**item.model_dump(exclude={"indice"}))
        for item in result.fragmentos
        if 0 <= item.indice < len(texts)
    }

def _classify_batch(batch: List[str]) -> List[ChunkPedagogicalInfo]:
    """
    Clasifica un lote. Los fragmentos que el LLM omita se reintentan juntos una vez.
    La clasificación solo ordena prioridades al seleccionar contexto; no es contenido.
    Por eso un fallo del proveedor deja la clase por defecto (sin guardarla en caché)
    en vez de cortar la solicitud, también en modo estricto.
    """
    found: Dict[int, ChunkPedagogicalInfo] = {}
    pending = list(range(len(batch)))
    for _intento in range(2):
        try:
            respuesta = _enrich_batch([batch[i] for i in pending])
        except Exception as error:
            logger.warning("Clasificación de fragmentos no disponible (%s); se usa la clase por defecto.", type(error).__name__)
            break
        for local_index, info in respuesta.items():
            found[pending[local_index]] = info
        pending = [i for i in pending if i not in found]
        if not pending:
            break
    infos = []
    for i, text in enumerate(batch):
        if i in found:
            _write_cache(text, found[i])
            infos.append(found[i])
        else:
            infos.append(_default_info())
    return infos

def enrich_chunks_metadata(texts: List[str]) -> List[ChunkPedagogicalInfo]:
    """
    Clasifica los fragmentos en lotes de BATCH_SIZE, reutilizando la caché.
    Hasta CONCURRENCY lotes se envían a la vez: en serie, un documento grande
    agotaba el presupuesto de tiempo del pipeline. Un texto repetido se clasifica una vez.
    """
    results: List[Optional[ChunkPedagogicalInfo]] = [_read_cache(text) for text in texts]
    pending = list(dict.fromkeys(text for text, info in zip(texts, results) if info is None))
    batches = [pending[start:start + BATCH_SIZE] for start in range(0, len(pending), BATCH_SIZE)]

    classified: Dict[str, ChunkPedagogicalInfo] = {}
    if batches:
        with ThreadPoolExecutor(max_workers=min(CONCURRENCY, len(batches))) as pool:
            for batch, infos in zip(batches, pool.map(_classify_batch, batches)):
                classified.update(zip(batch, infos))

    return [info if info is not None else classified[text] for text, info in zip(texts, results)]

def _approximate_token_length(text: str) -> int:
    return int(len(text.split()) * 1.3)

def _clean_header_title(title: str) -> str:
    return re.sub(r"[*_`]+", "", title).strip()

class SplitPiece(NamedTuple):
    text: str              # Texto final del chunk, con el contexto de sus títulos
    start: int             # Posición del chunk en el texto original
    end: int
    section: Optional[str]

class StructuralSplitter:
    def __init__(self, chunk_size=800, chunk_overlap=150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=_approximate_token_length,
            separators=["\n\n# ", "\n\n## ", "\n\n### ", "\n\n", "\n", ". ", " ", ""]
        )

    def _extract_protected_blocks(self, text: str) -> Tuple[str, Dict[str, str]]:
        blocks = {}
        # Protect code blocks
        for match in CODE_PATTERN.finditer(text):
            block = match.group(0)
            placeholder = f"__PROTECTED_BLOCK_{uuid.uuid4().hex}__"
            blocks[placeholder] = block
            text = text.replace(block, placeholder, 1)

        # Protect markdown tables
        table_pattern = re.compile(r"(\n\|[^\n]+\|\n\|[\s\-\|:]+\|\n(?:\|[^\n]+\|\n?)+)", re.MULTILINE)
        for match in table_pattern.finditer("\n" + text): # Prefix with \n to match start of table
            block = match.group(1).strip()
            if not block: continue
            placeholder = f"__PROTECTED_BLOCK_{uuid.uuid4().hex}__"
            blocks[placeholder] = block
            text = text.replace(block, placeholder, 1)

        return text, blocks

    def _restore_protected_blocks(self, chunks: List[str], blocks: Dict[str, str]) -> List[str]:
        restored_chunks = []
        for chunk in chunks:
            restored = chunk
            for placeholder, block in blocks.items():
                if placeholder in restored:
                    restored = restored.replace(placeholder, block)
            restored_chunks.append(restored)
        return restored_chunks

    def _header_positions(self, text: str) -> List[Tuple[int, str]]:
        # Los bloques de código se enmascaran conservando las posiciones,
        # para que un comentario "# ..." no se confunda con un título.
        masked = CODE_PATTERN.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
        return [(m.start(), m.group(0)) for m in HEADER_PATTERN.finditer(masked)]

    def _locate_chunks(self, text: str, chunks: List[str]) -> List[int]:
        # Los chunks son subcadenas del texto original; el solapamiento obliga
        # a buscar cada uno a partir del inicio del anterior.
        starts = []
        cursor = 0
        for chunk in chunks:
            pos = text.find(chunk, cursor)
            if pos == -1:
                pos = text.find(chunk[:200], cursor)
            if pos == -1:
                pos = cursor
            starts.append(pos)
            cursor = pos + 1
        return starts

    def _segments(self, text: str, headers: List[Tuple[int, str]]) -> List[Tuple[int, int]]:
        """
        Tramos que nunca se mezclan en un mismo fragmento: una sección por título y,
        sin títulos, grupos de párrafos de hasta PARAGRAPH_GROUP_TOKENS. Así, en un documento
        corto cada ítem generado puede citar la sección de la que proviene; antes todo el
        documento quedaba en un único fragmento F1.
        """
        if headers:
            limits = [0] + [offset for offset, _ in headers] + [len(text)]
            return [(a, b) for a, b in zip(limits, limits[1:]) if text[a:b].strip()]
        # Los bloques de código se enmascaran (sin saltos de línea) para no partirlos en sus
        # líneas en blanco; con un carácter visible, el bloque cuenta como un párrafo entero.
        masked = CODE_PATTERN.sub(lambda m: "x" * len(m.group(0)), text)
        paragraphs = [(m.start(), m.end()) for m in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\s*\Z)", masked, re.DOTALL)]
        segments, start, end, tokens = [], None, None, 0
        for p_start, p_end in paragraphs:
            p_tokens = _approximate_token_length(text[p_start:p_end])
            if start is not None and tokens + p_tokens > PARAGRAPH_GROUP_TOKENS:
                segments.append((start, end))
                start, tokens = None, 0
            if start is None:
                start = p_start
            end, tokens = p_end, tokens + p_tokens
        if start is not None:
            segments.append((start, end))
        return segments

    def split_with_sections(self, text: str) -> List[SplitPiece]:
        headers = self._header_positions(text)
        header_offsets = [offset for offset, _ in headers]
        # Un subtítulo pertenece a los encabezados de menor nivel que lo preceden.
        # Al pasar a una sección hermana se descarta la rama anterior, no sus ancestros.
        hierarchy: List[Tuple[int, str]] = []
        header_paths: List[List[str]] = []
        for _, header_line in headers:
            level = len(HEADER_PATTERN.match(header_line).group(1))
            while hierarchy and hierarchy[-1][0] >= level:
                hierarchy.pop()
            hierarchy.append((level, header_line))
            header_paths.append([line for _, line in hierarchy])

        located: List[Tuple[str, int]] = []
        for seg_start, seg_end in self._segments(text, headers):
            segment = text[seg_start:seg_end]
            if _approximate_token_length(segment) <= self.chunk_size:
                leading = len(segment) - len(segment.lstrip())
                located.append((segment.strip(), seg_start + leading))
                continue
            # Sección extensa: se divide por tamaño con solapamiento, protegiendo código y tablas
            protected_text, blocks = self._extract_protected_blocks(segment)
            chunks = self._restore_protected_blocks(self.text_splitter.split_text(protected_text), blocks)
            located.extend((chunk, seg_start + rel) for chunk, rel in zip(chunks, self._locate_chunks(segment, chunks)))

        pieces = []
        for chunk, start in located:
            if not chunk or HEADER_PATTERN.fullmatch(chunk.strip()):
                # Los títulos sin texto propio se conservan en el contexto de sus descendientes.
                continue
            index = bisect_right(header_offsets, start) - 1
            path = header_paths[index] if index >= 0 else []
            prefix = path[:-1] if path and chunk.startswith(path[-1]) else path
            final_text = "\n\n".join([*prefix, chunk])
            section = " > ".join(_clean_header_title(HEADER_PATTERN.match(line).group(2)) for line in path)
            pieces.append(SplitPiece(final_text, start, start + len(chunk), section or None))
        return pieces

    def split_text(self, text: str) -> List[str]:
        return [piece.text for piece in self.split_with_sections(text)]

def generate_chunk_id(doc_id: str, index: int) -> str:
    return f"{doc_id}-chk-{index:04d}"

def _page_at(page_offsets: List[int], pages: List[Optional[int]], position: int) -> Optional[int]:
    index = bisect_right(page_offsets, position) - 1
    return pages[max(index, 0)]

def perform_structural_chunking(document_id: str, contents: List[ExtractedContent]) -> List[Chunk]:
    """
    Segmenta el documento completo (no página por página), de modo que un
    concepto que cruza un salto de página no quede partido sin solapamiento.
    Cada chunk conserva la página donde empieza (page) y donde termina (page_end).
    """
    if not contents:
        return []

    page_offsets: List[int] = []
    pages: List[Optional[int]] = []
    offset = 0
    for content in contents:
        page_offsets.append(offset)
        pages.append(content.metadata.page)
        offset += len(content.text) + len(PAGE_JOINER)
    full_text = PAGE_JOINER.join(content.text for content in contents)

    # Sin clasificación pedagógica: AI Core clasifica solo los fragmentos candidatos
    # cuando el documento no entra completo en el contexto (ver enrich_chunks_metadata).
    pieces = StructuralSplitter().split_with_sections(full_text)
    source_meta = contents[0].metadata

    chunks = []
    for chunk_index, piece in enumerate(pieces, start=1):
        chunk_meta = ChunkMetadata(
            document_id=document_id,
            chunk_id=generate_chunk_id(document_id, chunk_index),
            name=source_meta.name,
            doc_type=source_meta.doc_type,
            source=source_meta.source,
            page=_page_at(page_offsets, pages, piece.start),
            page_end=_page_at(page_offsets, pages, max(piece.end - 1, piece.start)),
            section=piece.section,
        )
        chunks.append(Chunk(text=piece.text, metadata=chunk_meta))

    return chunks
