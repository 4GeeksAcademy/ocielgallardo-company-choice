"""HealthCore knowledge assistant as an explicit LangGraph.

Responsibility: expose the existing RAG behavior (``retrieve`` + ``generate_answer``
from ``data.pipelines.rag``) as a compiled graph with single-responsibility nodes,
explicit conditional edges, a minimal state, per-run traces, and checkpointing.

Node contract (binding):
- ``receive_node`` normalizes the question only (no retrieval, no LLM).
- ``retrieve_node`` calls ONLY ``retrieve(question)``.
- ``generate_node`` calls ONLY ``generate_answer(question, context)`` with the
  context the retrieve node already produced.
- ``refuse_node`` answers a blank question with the existing honest fallback
  (no retrieval, no LLM).
- ``honest_node`` answers empty retrieval with ``generate_answer(question, [])``
  — the same honest empty-context path ``query()`` takes today, as its own node.
- No node imports or calls the monolithic ``query()`` (it would re-run retrieval
  and collapse the flow this graph makes explicit).

The graph is compiled at import time (with a ``MemorySaver`` checkpointer) so
structural errors fail fast, not in production. Services call :func:`run_agent`
and read ``result["answer"]`` — the HTTP contract (``{question, answer}`` only)
is unchanged; traces stay internal.

Run a question locally:
    uv run python -m data.pipelines.agent_graph "what do I need to bring to my first appointment?"
"""

from __future__ import annotations

import contextvars
import logging
import sys
import time
import uuid
from collections import OrderedDict
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from data.pipelines import rag as rag_pipeline

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Minimal state travelling between nodes. No history, no vectors."""

    question: str
    context: list[dict]
    answer: str


# --- Internal per-run trace store (queryable, bounded, no PHI beyond the question) ---

_MAX_TRACES = 100
_TRACES: OrderedDict[str, dict] = OrderedDict()
_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "agent_graph_trace_id", default=None
)


def _record_span(
    node: str, started_at: float, finished_at: float, output: dict | None = None
) -> None:
    trace_id = _current_trace_id.get()
    if trace_id is None:
        return
    trace = _TRACES.get(trace_id)
    if trace is None:
        return
    trace["spans"].append(
        {
            "node": node,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": round((finished_at - started_at) * 1000, 2),
            "output": output or {},
        }
    )


def get_trace(trace_id: str) -> dict | None:
    """Return the stored trace for ``trace_id`` (copy), or ``None``."""
    trace = _TRACES.get(trace_id)
    return dict(trace) if trace is not None else None


def get_last_trace() -> dict | None:
    """Return the most recent stored trace (copy), or ``None``."""
    if not _TRACES:
        return None
    return dict(next(reversed(_TRACES.values())))


def get_agent_state(trace_id: str) -> dict | None:
    """Return the checkpointed graph state for a past run, or ``None``."""
    try:
        snapshot = graph.get_state({"configurable": {"thread_id": trace_id}})
    except Exception:
        logger.exception("Could not read checkpoint for run %s", trace_id)
        return None
    if not snapshot.values:
        return None
    return dict(snapshot.values)


def _store_trace(trace: dict) -> None:
    _TRACES[trace["trace_id"]] = trace
    while len(_TRACES) > _MAX_TRACES:
        _TRACES.popitem(last=False)


# --- Nodes: one responsibility each, delegating to the existing RAG functions ---


def receive_node(state: AgentState) -> dict:
    """Normalize the incoming question (strip whitespace). No I/O."""
    started = time.time()
    question = ""
    try:
        question = state["question"].strip()
        return {"question": question}
    finally:
        _record_span(
            "receive", started, time.time(), {"question_chars": len(question)}
        )


def retrieve_node(state: AgentState) -> dict:
    """Retrieve policy chunks for ``state['question']`` via ``retrieve()``."""
    started = time.time()
    context: list[dict] = []
    try:
        context = rag_pipeline.retrieve(state["question"])
        return {"context": context}
    finally:
        _record_span(
            "retrieve",
            started,
            time.time(),
            {
                "n_chunks": len(context),
                "sources": sorted(
                    {str(chunk.get("source_document", "")) for chunk in context}
                ),
            },
        )


def generate_node(state: AgentState) -> dict:
    """Generate the answer from ``question`` + already-retrieved ``context``."""
    started = time.time()
    answer = ""
    try:
        answer = rag_pipeline.generate_answer(state["question"], state["context"])
        return {"answer": answer}
    finally:
        _record_span(
            "generate", started, time.time(), {"answer_chars": len(answer)}
        )


def refuse_node(state: AgentState) -> dict:
    """Answer a blank question honestly without retrieval or LLM."""
    started = time.time()
    try:
        return {"answer": rag_pipeline.INSUFFICIENT_INFO_ANSWER}
    finally:
        _record_span("refuse", started, time.time(), {"reason": "blank_question"})


def honest_node(state: AgentState) -> dict:
    """Answer empty retrieval honestly via the existing empty-context path."""
    started = time.time()
    answer = ""
    try:
        answer = rag_pipeline.generate_answer(state["question"], [])
        return {"answer": answer}
    finally:
        _record_span(
            "honest", started, time.time(), {"answer_chars": len(answer)}
        )


# --- Conditional edges: explicit routing, never a hardcoded straight line ---


def route_question(state: AgentState) -> Literal["refuse", "retrieve"]:
    """Blank question short-circuits to ``refuse``; otherwise retrieve."""
    return "refuse" if not state["question"].strip() else "retrieve"


def route_context(state: AgentState) -> Literal["honest", "generate"]:
    """Empty retrieval routes to ``honest``; otherwise generate."""
    return "honest" if not state["context"] else "generate"


_checkpointer = MemorySaver()

_builder = StateGraph(AgentState)
_builder.add_node("receive", receive_node)
_builder.add_node("retrieve", retrieve_node)
_builder.add_node("generate", generate_node)
_builder.add_node("refuse", refuse_node)
_builder.add_node("honest", honest_node)
_builder.add_edge(START, "receive")
_builder.add_conditional_edges("receive", route_question)
_builder.add_conditional_edges("retrieve", route_context)
_builder.add_edge("refuse", END)
_builder.add_edge("honest", END)
_builder.add_edge("generate", END)

# Compiled at import time: structural errors surface on import, not in production.
graph = _builder.compile(checkpointer=_checkpointer)


def run_agent(question: str) -> dict:
    """Run the compiled graph for ``question`` and return the final state + trace id.

    Returns ``{"question": ..., "context": [...], "answer": ...,
    "trace_id": ...}``. The answer is always model-generated (or the honest
    fallback for blank questions), never raw hits.
    """
    trace_id = uuid.uuid4().hex
    started = time.time()
    trace: dict = {
        "trace_id": trace_id,
        "thread_id": trace_id,
        "question": question,
        "started_at": started,
        "finished_at": started,
        "duration_ms": 0.0,
        "status": "running",
        "n_chunks": 0,
        "sources": [],
        "spans": [],
        "error": None,
    }
    _store_trace(trace)
    token = _current_trace_id.set(trace_id)
    try:
        result = graph.invoke(
            {"question": question, "context": [], "answer": ""},
            {"configurable": {"thread_id": trace_id}},
        )
        finished = time.time()
        context = result.get("context", [])
        trace.update(
            {
                "finished_at": finished,
                "duration_ms": round((finished - started) * 1000, 2),
                "status": "success",
                "n_chunks": len(context),
                "sources": sorted(
                    {str(chunk.get("source_document", "")) for chunk in context}
                ),
            }
        )
        logger.info(
            "agent_graph run %s via %s in %.1fms",
            trace_id,
            [span["node"] for span in trace["spans"]],
            trace["duration_ms"],
        )
        return {**result, "trace_id": trace_id}
    except Exception as exc:
        finished = time.time()
        trace.update(
            {
                "finished_at": finished,
                "duration_ms": round((finished - started) * 1000, 2),
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        logger.exception("agent_graph run %s failed", trace_id)
        raise
    finally:
        _current_trace_id.reset(token)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: uv run python -m data.pipelines.agent_graph "your question"'
        )
    outcome = run_agent(sys.argv[1])
    print(outcome["answer"])
    print(f"[trace_id={outcome['trace_id']}]")
