"""RAG retrieval + generation (retrieve / generate_answer / query).

Responsibility: search ``healthcore_knowledge`` in Qdrant and generate the
final answer with the generation LLM from the retrieved context. The answer
is always model-generated — raw vector-DB hits are never returned.
``query()`` is literally ``retrieve()`` + ``generate_answer()`` so a later
agent can reuse each step separately. Services import these helpers
(no retrieval/generation logic in ``services/``).

Run a question locally:
    uv run python -m data.pipelines.rag "what do I need to bring to my first appointment?"
"""

from __future__ import annotations

import logging
import sys

from data.process.rag import RagSettings, embed

logger = logging.getLogger(__name__)

# Cosine-similarity floor: below this, chunks are typically off-topic for
# short front-desk policy questions, so the model must answer honestly
# instead of guessing. Tune with data/eval/test-queries.json
# (Recall@3 target >= 80%). See docs/rag/rag-design.md for the rationale.
DEFAULT_MIN_SCORE = 0.35
DEFAULT_TOP_K = 5

# Fallback when the model returns nothing usable — a constant template,
# never vector-DB text.
INSUFFICIENT_INFO_ANSWER = (
    "I don't have enough information in the clinic policies to answer that. "
    "Please verify it with billing or the clinic front desk."
)

SYSTEM_PROMPT = """You are the knowledge assistant for HealthCore patient coordinators. \
Answer the way the clinic's best service salesperson would: clear, empathetic, and concise.

Hard rules:
- Use ONLY the retrieved policy context below. Never invent coverage, fees, documents, or timeframes.
- If no context was retrieved, or it does not answer the question, say the knowledge base has no relevant information and ask to verify with billing or the front desk.
- For insurance questions without a specified country, explicitly distinguish United States vs United Kingdom.
- For coverage not listed in the context, state it must be verified with billing — never confirm undocumented coverage.
- No-show fees must never be applied to Medicare or Medicaid patients; follow the appointment policy literally.
- Never include patient data: policies and procedures only."""


def retrieve(
    query: str, *, k: int = DEFAULT_TOP_K, min_score: float = DEFAULT_MIN_SCORE
) -> list[dict]:
    """Embed the question and return surviving chunk payloads (never SDK objects).

    Searches the ``k`` nearest neighbours in Qdrant and drops anything below
    ``min_score`` — fewer than ``k`` results may come back.
    """
    from data.process.rag import _get_qdrant_client

    settings = RagSettings.from_env()
    question_vector = embed(query, settings=settings)

    client = _get_qdrant_client(settings)
    try:
        result = client.query_points(
            collection_name=settings.collection,
            query=question_vector,
            limit=k,
        )
    finally:
        client.close()

    return [
        dict(point.payload or {})
        for point in result.points
        if point.score is not None and point.score >= min_score
    ]


def build_prompt(question: str, context: list[dict]) -> str:
    """Assemble the generation prompt from retrieved payloads (no I/O)."""
    if context:
        context_blocks = "\n\n".join(
            f"[source: {chunk.get('source_document', '')} "
            f"| section: {chunk.get('section', '')}]\n{chunk.get('text', '')}"
            for chunk in context
        )
    else:
        context_blocks = "(no relevant context retrieved)"
    return (
        f"{SYSTEM_PROMPT}\n\nRetrieved policy context:\n{context_blocks}\n\n"
        f"Coordinator question: {question}\nAnswer:"
    )


def generate_answer(question: str, context: list[dict]) -> str:
    """Generate the final answer from ``question`` + retrieved ``context``.

    Standalone step (no retrieval inside) so a later agent can call
    ``retrieve()`` and ``generate_answer()`` separately without running
    retrieval twice.
    """
    from openai import OpenAI

    settings = RagSettings.from_env()
    if not settings.llm_model:
        raise RuntimeError(
            "LLM_MODEL is not set. Add the 4Geeks-provided "
            "generation model ID to .env."
        )
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not set. Add it to .env (gitignored).")
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)
    completion = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(question, context)},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    text = (completion.choices[0].message.content or "").strip()
    return text or INSUFFICIENT_INFO_ANSWER


def query(question: str) -> str:
    """Answer a coordinator question. The only function external consumers call.

    Literally ``retrieve()`` + ``generate_answer()``: the final string is
    always model-generated, never raw Qdrant output. With no above-threshold
    context, the model answers honestly from the empty-context prompt.
    """
    return generate_answer(question, retrieve(question))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        raise SystemExit('Usage: uv run python -m data.pipelines.rag "your question"')
    print(query(sys.argv[1]))
