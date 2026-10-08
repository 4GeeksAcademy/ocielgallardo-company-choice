"""RAG chunking + indexation (setup / embed) for the HealthCore knowledge base.

Responsibility: read ``docs/company-knowledge-base/*.md``, split documents
into payload-shaped chunks, embed them, and upsert them into Qdrant.

No FastAPI imports here and no network calls at import time — clients are
built lazily inside functions so unit tests can exercise chunking offline.

Run:
    uv run python -m data.process.rag
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Qdrant collection name required by the milestone brief.
DEFAULT_COLLECTION = "healthcore_knowledge"

# Expected corpus files (filename stem -> source_document payload value).
# Both English (.en) and Spanish (.es) sources map to the same document ids;
# language is detected from the suffix at load time.
SOURCE_DOCUMENTS = {
    "healthcore-insurance-coverage.en": "insurance-coverage",
    "healthcore-appointment-policy.en": "appointment-policy",
    "healthcore-referral-process.en": "referral-process",
    "healthcore-new-patient-checklist.en": "new-patient-checklist",
    "healthcore-insurance-coverage.es": "insurance-coverage",
    "healthcore-appointment-policy.es": "appointment-policy",
    "healthcore-referral-process.es": "referral-process",
    "healthcore-new-patient-checklist.es": "new-patient-checklist",
}

# Seed requirement: every source document must produce at least 3 chunks.
MIN_CHUNKS_PER_DOCUMENT = 3

# Chunking budget: pack paragraphs up to ~400 chars, keep 1 paragraph overlap
# so section boundaries stay searchable without duplicating whole sections.
# (~1KB source docs need a ~400 budget to reach the seed minimum of 3 chunks
# per document; packing still only splits at paragraph boundaries, never
# mid-sentence.)
CHUNK_TARGET_CHARS = 400
CHUNK_OVERLAP_PARAGRAPHS = 1

_HEADING_RE = re.compile(r"^#{1,6}\s+(.*\S)\s*$")


@dataclass(frozen=True)
class RagSettings:
    """Environment-driven configuration (keys/URLs live in root .env).

    Separate model IDs: ``EMBEDDING_MODEL`` (OpenRouter) for vectors and
    ``LLM_MODEL`` (Groq OpenAI-compatible) for generation.
    """

    qdrant_url: str
    collection: str
    embedding_api_key: str
    embedding_api_url: str
    embedding_model: str
    embedding_dim: int
    llm_api_key: str
    llm_api_url: str
    llm_model: str

    @classmethod
    def from_env(cls) -> RagSettings:
        try:
            embedding_dim = int(os.getenv("EMBEDDING_DIM", "2048"))
        except ValueError:
            embedding_dim = 2048
        return cls(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            collection=os.getenv("RAG_COLLECTION", DEFAULT_COLLECTION),
            embedding_api_key=os.getenv("EMBEDDING_API_KEY", ""),
            embedding_api_url=os.getenv(
                "EMBEDDING_API_URL", "https://openrouter.ai/api/v1"
            ),
            embedding_model=os.getenv("EMBEDDING_MODEL", ""),
            embedding_dim=embedding_dim,
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_api_url=os.getenv("LLM_API_URL", "https://api.groq.com/openai/v1"),
            llm_model=os.getenv("LLM_MODEL", ""),
        )


def chunk_markdown(
    text: str,
    *,
    source_document: str,
    language: str = "en",
) -> list[dict]:
    """Split a markdown document into payload-shaped chunks.

    Headings become the ``section`` label; paragraphs are greedily packed up
    to ``CHUNK_TARGET_CHARS`` with a one-paragraph overlap. Pure function —
    no I/O, no network.
    """
    sections: list[tuple[str, list[str]]] = []
    current_section = "overview"
    current_paragraphs: list[str] = []

    def _flush() -> None:
        if any(p.strip() for p in current_paragraphs):
            sections.append((current_section, list(current_paragraphs)))
        current_paragraphs.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading = _HEADING_RE.match(line)
        if heading:
            _flush()
            current_section = heading.group(1)
            continue
        if not line:
            continue
        if current_paragraphs and len(current_paragraphs[-1]) < CHUNK_TARGET_CHARS:
            current_paragraphs[-1] = f"{current_paragraphs[-1]} {line}"
        else:
            current_paragraphs.append(line)
    _flush()

    chunks: list[dict] = []
    for section, paragraphs in sections:
        window: list[str] = []
        window_chars = 0
        for paragraph in paragraphs:
            if window and window_chars + len(paragraph) > CHUNK_TARGET_CHARS:
                chunks.append(_make_chunk(chunks, source_document, section, language, window))
                window = window[-CHUNK_OVERLAP_PARAGRAPHS:] if CHUNK_OVERLAP_PARAGRAPHS else []
                window_chars = sum(len(p) for p in window)
            window.append(paragraph)
            window_chars += len(paragraph)
        if any(p.strip() for p in window):
            chunks.append(_make_chunk(chunks, source_document, section, language, window))

    # Re-index sequentially so chunk_index is stable per document.
    for index, chunk in enumerate(chunks):
        chunk["chunk_index"] = index
    return chunks


def _make_chunk(
    existing: list[dict],
    source_document: str,
    section: str,
    language: str,
    paragraphs: list[str],
) -> dict:
    return {
        "company": "healthcore",
        "source_document": source_document,
        "section": section,
        "language": language,
        "chunk_index": len(existing),
        "text": "\n".join(paragraphs).strip(),
    }


def load_corpus(directory: str | Path) -> list[dict]:
    """Read ``*.md`` files and return payload-shaped chunks.

    Unknown filenames are skipped with a warning so the payload schema
    (``source_document`` enum) stays strict. Raises ``FileNotFoundError``
    with the expected file list when the corpus is missing.
    """
    corpus_dir = Path(directory)
    if not corpus_dir.is_dir():
        expected = sorted(f"{stem}.md" for stem in SOURCE_DOCUMENTS)
        raise FileNotFoundError(
            f"RAG corpus not found at {corpus_dir}. "
            f"Copy the source documents ({', '.join(expected)}) into it first."
        )
    chunks: list[dict] = []
    for path in sorted(corpus_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        source_document = SOURCE_DOCUMENTS.get(path.stem)
        if source_document is None:
            logger.warning("Skipping %s: not a known source document", path.name)
            continue
        language = "en" if path.stem.endswith(".en") else "es"
        doc_chunks = chunk_markdown(
            path.read_text(encoding="utf-8"),
            source_document=source_document,
            language=language,
        )
        if len(doc_chunks) < MIN_CHUNKS_PER_DOCUMENT:
            logger.warning(
                "%s produced %d chunks (seed requires >= %d)",
                path.name,
                len(doc_chunks),
                MIN_CHUNKS_PER_DOCUMENT,
            )
        chunks.extend(doc_chunks)
    if not chunks:
        expected = sorted(f"{stem}.md" for stem in SOURCE_DOCUMENTS)
        raise FileNotFoundError(
            f"No indexable documents in {corpus_dir}. "
            f"Expected: {', '.join(expected)}."
        )
    return chunks


def _require_embedding_config(resolved: RagSettings) -> None:
    if not resolved.embedding_model:
        raise RuntimeError(
            "EMBEDDING_MODEL is not set. Add the 4Geeks-provided "
            "embedding model ID to .env (never reuse the generation model)."
        )
    if resolved.llm_model and resolved.embedding_model == resolved.llm_model:
        raise ValueError(
            "EMBEDDING_MODEL must differ from LLM_MODEL: "
            "never reuse the generation model for embeddings."
        )
    if not resolved.embedding_api_key:
        raise RuntimeError(
            "EMBEDDING_API_KEY is not set. Add it to .env (gitignored)."
        )


def embed(text: str, *, settings: RagSettings | None = None) -> list[float]:
    """Embed one text via OpenRouter (OpenAI-compatible ``openai`` SDK).

    The single embedding entry point: used both for chunks at index time
    (``setup()``) and for the user question at query time (``retrieve()``).
    Never uses the generation model (separate ``LLM_MODEL`` ID).
    """
    from openai import OpenAI

    resolved = settings or RagSettings.from_env()
    _require_embedding_config(resolved)
    client = OpenAI(
        api_key=resolved.embedding_api_key,
        base_url=resolved.embedding_api_url,
    )
    response = client.embeddings.create(model=resolved.embedding_model, input=text)
    vector = list(response.data[0].embedding)
    if resolved.embedding_dim and len(vector) != resolved.embedding_dim:
        logger.warning(
            "Embedding dim mismatch: got %d, EMBEDDING_DIM=%d",
            len(vector),
            resolved.embedding_dim,
        )
    return vector


def embed_texts(texts: list[str], *, settings: RagSettings | None = None) -> list[list[float]]:
    """Embed a batch by delegating to :func:`embed` (same function, same model)."""
    resolved = settings or RagSettings.from_env()
    return [embed(text, settings=resolved) for text in texts]


def _get_qdrant_client(settings: RagSettings):
    from qdrant_client import QdrantClient

    return QdrantClient(url=settings.qdrant_url, timeout=10)


def chunk_point_id(collection: str, source_document: str, chunk_index: int) -> str:
    """Deterministic point ID so re-running ``setup()`` upserts, never duplicates."""
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{collection}:{source_document}:{chunk_index}",
        )
    )


def setup(
    corpus_dir: str | Path = "docs/company-knowledge-base",
    *,
    settings: RagSettings | None = None,
    recreate: bool = False,
) -> dict:
    """Chunk the corpus, embed it, and upsert it into Qdrant.

    Idempotent by design: point IDs are deterministic
    (``chunk_point_id`` over collection + source + chunk index), so a
    re-run overwrites the same points instead of duplicating them.
    Creates the collection on first run (Cosine distance, size inferred
    from the embedding model). Never drops an existing collection unless
    ``recreate=True`` is passed explicitly.
    """
    from qdrant_client.models import Distance, PointStruct, VectorParams

    resolved = settings or RagSettings.from_env()
    chunks = load_corpus(corpus_dir)
    vectors = embed_texts([chunk["text"] for chunk in chunks], settings=resolved)

    client = _get_qdrant_client(resolved)
    try:
        if recreate:
            client.delete_collection(resolved.collection)
        if not client.collection_exists(resolved.collection):
            client.create_collection(
                collection_name=resolved.collection,
                vectors_config=VectorParams(
                    size=len(vectors[0]), distance=Distance.COSINE
                ),
            )
        points = [
            PointStruct(
                id=chunk_point_id(
                    resolved.collection,
                    str(chunk["source_document"]),
                    int(chunk["chunk_index"]),
                ),
                vector=vector,
                payload=chunk,
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        client.upsert(collection_name=resolved.collection, points=points)
    finally:
        client.close()

    by_document: dict[str, int] = {}
    for chunk in chunks:
        key = str(chunk["source_document"])
        by_document[key] = by_document.get(key, 0) + 1
    return {
        "collection": resolved.collection,
        "documents": len(by_document),
        "chunks": len(chunks),
        "chunks_by_document": by_document,
        "vector_size": len(vectors[0]),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stats = setup()
    print(stats)
