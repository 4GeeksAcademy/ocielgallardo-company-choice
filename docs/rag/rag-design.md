# RAG Design — HealthCore Knowledge Assistant

## 1. Purpose

Front-desk patient coordinators answer the same prospect/client questions
repeatedly (insurance, cancellations, referrals, first visits). The assistant
responds in the voice of the clinic's best service salesperson — clear,
empathetic, never inventing coverage or policies — so coordinators stop
hunting through dispersed documents.

Audience: the 8 patient coordinators led by Priya Nair (Patient Experience).

## 2. End-to-end flow

```mermaid
flowchart LR
    DOCS[docs/company-knowledge-base/*.md] --> SETUP[setup() in data/process/rag.py]
    SETUP --> EMBED[embed() via OpenRouter]
    EMBED --> QDRANT[(Qdrant: healthcore_knowledge)]
    Q[coordinator question] --> RETRIEVE[retrieve() in data/pipelines/rag.py]
    RETRIEVE --> QDRANT
    RETRIEVE --> GEN[generate_answer() -> Groq LLM]
    GEN --> QUERY[query() = retrieve + generate]
    QUERY --> API[POST /knowledge/query]
    API --> UI[/knowledge in backoffice]
```

Numbered:

1. Source markdown lives in `docs/company-knowledge-base/` (four files,
   §3). `setup()` chunks, embeds via `embed()`, and upserts into Qdrant.
2. A coordinator asks from `/knowledge`; the backoffice calls
   `POST /knowledge/query` with `{ "question": "..." }` (Bearer).
3. The router calls `query(question)` — the only function consumers call.
4. `query()` runs `retrieve()` (embed question with the same `embed()`,
   top-k nearest, `min_score` filter) then `generate_answer()` (prompt +
   LLM call) and returns the final string.
5. The endpoint answers `{ "question": ..., "answer": ... }` — model text
   only, never Qdrant chunks or scores.
6. A later agent can call `retrieve()` and `generate_answer()` separately
   without double retrieval or unwrapping `query()`.

## 3. Chunking strategy

Hybrid heading + paragraph packing (`chunk_markdown` in
`data/process/rag.py`):

- Markdown headings (`#`–`######`) become the chunk `section`, so each
  policy rule keeps its titled unit (e.g. a cancellation-fee clause never
  merges with unrelated sections).
- Paragraphs pack greedily to ~800 chars with a 1-paragraph overlap, so a
  rule split across a boundary still appears whole in a neighbour chunk.
  Sentences are never cut mid-line: packing only joins/splits at paragraph
  boundaries.
- Text preprocessing is minimal and documented: lines are stripped, blank
  lines dropped, paragraphs joined with single spaces — no lowercasing, no
  stop-word removal, so fees, timeframes, and plan names embed verbatim.

Why it fits: the corpus is short policy/procedure documents where the
semantic unit is the titled rule/condition, not a fixed token window.
Heading-scoped chunks keep one rule per chunk; the overlap preserves
conditions that span paragraphs.

- TODO: record per-document chunk counts after indexing (each of the four
  documents must yield ≥ 3 chunks).

## 4. Embeddings and generation (separate models)

- Embeddings: `EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b:free` via
  `EMBEDDING_API_URL` (OpenRouter, OpenAI-compatible `openai` SDK),
  4Geeks-provided. Dim `EMBEDDING_DIM=2048`; `setup()` warns on mismatch.
- Generation: `LLM_MODEL=qwen/qwen3.8-27b` via `LLM_API_URL` (Groq
  OpenAI-compatible), `temperature=0.2`, `max_tokens=512` for short desk
  answers. 4Geeks-provided.
- `embed(text)` is the single entry point used both at index time
  (`setup()` → `embed_texts()` delegates to it) and at query time
  (`retrieve()`), guaranteeing identical preprocessing and model.
  `setup()` raises if `EMBEDDING_MODEL == LLM_MODEL`.
- Qdrant: Cosine distance; collection `healthcore_knowledge` (override via
  `RAG_COLLECTION`).

## 5. Similarity threshold and tuning

`retrieve(query, *, k=5, min_score=0.35)`: nearest 5, drop below 0.35
cosine — fewer than `k` may return. Rationale: for short front-desk policy
questions, chunks below ~0.35 are typically off-topic; answering from them
risks unfaithful fees/coverage, so the model instead answers honestly from
the empty-context prompt. Tuning procedure: run
`uv run python data/eval/measure_rag_recall.py` (Recall@3 on
`data/eval/test-queries.json`, target ≥ 80%); if recall misses, lower the
floor in small steps and re-check faithfulness on the same set.

## 6. Idempotency

`setup()` is idempotent by deterministic IDs: each point ID is
`uuid5(collection, source_document, chunk_index)`, so re-running overwrites
the same points instead of duplicating them (chosen over wipe-and-reload to
avoid a window with an empty collection). Pass `recreate=True` only for an
explicit full rebuild (e.g. embedding-model change).

## 7. Acceptance notes

- The final answer is always model-generated from retrieved context.
- Faithfulness: no coverage/fee/timeframe outside the chunks; unlisted
  coverage → verify with billing; US/UK distinguished when unspecified;
  no-show fees never applied to Medicare/Medicaid.
- No PHI is indexed or generated at any point (HIPAA / UK GDPR).

## 8. Gaps (TODO)

- TODO: `00-general-contexts/healthcore/` is absent — copy the four source
  documents into `docs/company-knowledge-base/` and run `setup()`.
- TODO: set `EMBEDDING_API_KEY` / `LLM_API_KEY` in local `.env` (gitignored).
- TODO: confirm `LLM_MODEL` serves through `LLM_API_URL` with the provider.
- TODO: measure Recall@3 with `measure_rag_recall.py` after indexing.
- TODO: decide whether `/knowledge/query` stays Bearer-only for coordinators.
