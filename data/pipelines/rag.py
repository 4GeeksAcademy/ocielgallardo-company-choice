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

import contextvars
import logging
import sys
from collections.abc import Callable, Iterator
from data.process.rag import RagSettings, embed

logger = logging.getLogger(__name__)


class GenerationInterrupted(Exception):
    """Raised when a chat cancel_check aborts an in-flight LLM stream."""


# Optional stream hooks for WebSocket chat (Part 2). Nodes keep calling
# ``generate_answer``; when set, tokens are yielded via ``on_token``.
_StreamHooks = tuple[Callable[[str], None], Callable[[], bool]]
_stream_hooks: contextvars.ContextVar[_StreamHooks | None] = contextvars.ContextVar(
    "rag_stream_hooks", default=None
)


def set_stream_hooks(
    on_token: Callable[[str], None] | None,
    cancel_check: Callable[[], bool] | None,
) -> contextvars.Token:
    """Install or clear stream hooks for the current context."""
    if on_token is None or cancel_check is None:
        return _stream_hooks.set(None)
    return _stream_hooks.set((on_token, cancel_check))


def reset_stream_hooks(token: contextvars.Token) -> None:
    _stream_hooks.reset(token)

# Cosine-similarity floor: below this, chunks are typically off-topic for
# short front-desk policy questions, so the model must answer honestly
# instead of guessing. Tuned 0.35 -> 0.25 with data/eval/test-queries.json:
# insurance questions rank the right document first at 0.287-0.345, so 0.35
# returned empty context (Recall@3 75%); 0.25 admits them while keeping
# off-topic chunks (<= 0.24 on the eval set) out. See docs/rag/rag-design.md.
DEFAULT_MIN_SCORE = 0.25
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


def generate_answer_stream(
    question: str,
    context: list[dict],
    *,
    cancel_check: Callable[[], bool] | None = None,
) -> Iterator[str]:
    """Stream answer tokens from the generation LLM (``stream=True``).

    Raises :class:`GenerationInterrupted` if ``cancel_check`` returns True
    mid-stream so the caller can abort genuinely (not ignore a finished reply).
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
    stream = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(question, context)},
        ],
        temperature=0.2,
        max_tokens=512,
        stream=True,
    )
    emitted = False
    for chunk in stream:
        if cancel_check and cancel_check():
            raise GenerationInterrupted("chat generation cancelled")
        delta = ""
        try:
            delta = chunk.choices[0].delta.content or ""
        except (AttributeError, IndexError):
            delta = ""
        if not delta:
            continue
        emitted = True
        yield delta
    if not emitted:
        yield INSUFFICIENT_INFO_ANSWER


def generate_answer(question: str, context: list[dict]) -> str:
    """Generate the final answer from ``question`` + retrieved ``context``.

    Standalone step (no retrieval inside) so a later agent can call
    ``retrieve()`` and ``generate_answer()`` separately without running
    retrieval twice. When stream hooks are installed (WebSocket chat),
    tokens are forwarded via ``on_token`` without changing graph nodes.
    """
    from openai import OpenAI

    hooks = _stream_hooks.get()
    if hooks is not None:
        on_token, cancel_check = hooks
        parts: list[str] = []
        for token in generate_answer_stream(
            question, context, cancel_check=cancel_check
        ):
            on_token(token)
            parts.append(token)
        text = "".join(parts).strip()
        return text or INSUFFICIENT_INFO_ANSWER

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
