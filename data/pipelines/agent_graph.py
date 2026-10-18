"""HealthCore support agent as an explicit LangGraph (Part 2).

Responsibility: route each coordinator question to the right source —
stable knowledge via RAG (``retrieve`` + ``generate_answer``), live tickets
and stock via the MCP server tools — with
single-responsibility nodes, conditional routing, minimal state, per-run
traces, and checkpointing.

Node contract (binding):
- ``receive_node`` normalizes the question only (no retrieval, no LLM, no tools).
- ``decide_route_node`` classifies RAG vs incidents vs inventory vs hybrid.
- ``retrieve_node`` calls ONLY ``retrieve(question)``.
- ``generate_node`` calls ONLY ``generate_answer(question, context)``.
- ``lookup_incident_node`` / ``lookup_inventory_node`` call ONLY their
  MCP tool (MCP is the single transport — no direct HTTP fallback; never RAG,
  never each other).
- ``answer_from_tool_node`` surfaces successful tool data deterministically.
- ``synthesize_hybrid_node`` prefixes the deterministic tool fact block and
  appends the LLM policy paragraph (tool facts are never left to the model).
- ``tool_fallback_node`` answers honestly when a tool fails (no invented state).
- ``refuse_node`` / ``honest_node`` keep the Part 1 blank/empty-context paths.
- No node imports or calls the monolithic ``query()``.

The graph is compiled at import time (with a ``MemorySaver`` checkpointer) so
structural errors fail fast. Services call :func:`run_agent` and read
``result["answer"]`` — HTTP still returns ``{question, answer}`` only.

Run a question locally:
    uv run python -m data.pipelines.agent_graph "what is the status of ticket 2?"
"""

from __future__ import annotations

import contextvars
import logging
import re
import sys
import time
import uuid
from collections import OrderedDict
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from data.pipelines import mcp_client, rag as rag_pipeline
from data.pipelines.agent_tools import (
    INCIDENT_TOOL_FALLBACK,
    INVENTORY_TOOL_FALLBACK,
    IncidentToolInput,
    InventoryToolInput,
    format_incident_answer,
    format_inventory_answer,
)

logger = logging.getLogger(__name__)

# Ticket / incident phrasing that must not go to the policy RAG alone.
_TICKET_ID_RE = re.compile(
    r"\b(?:ticket|incident|caso|incidencia)\s*#?\s*(\d+)\b",
    re.IGNORECASE,
)
_TICKET_STATUS_RE = re.compile(
    r"\b(?:status|estado|state)\b.*\b(?:ticket|incident|caso|incidencia)\b"
    r"|\b(?:ticket|incident|caso|incidencia)\b.*\b(?:status|estado|state)\b",
    re.IGNORECASE,
)
_INCIDENT_KEYWORDS_RE = re.compile(
    r"\b(?:open tickets?|tickets? abiertos?|incident manager|"
    r"gestor de incidentes|support ticket)\b",
    re.IGNORECASE,
)
_SKU_RE = re.compile(r"\b(HCR-[A-Z]+-\d+)\b", re.IGNORECASE)
_INVENTORY_KEYWORDS_RE = re.compile(
    r"\b(?:stock|inventory|inventario|suministro|supply|supplies|"
    r"do we have|tenemos stock|hay stock|cu[aá]nto stock)\b",
    re.IGNORECASE,
)
# Policy/procedure phrasing that, combined with a live tool signal, is hybrid.
_POLICY_SIGNAL_RE = re.compile(
    r"\b(?:polic(?:y|ies)|procedure|procedimiento|pol[ií]tica|"
    r"cancel(?:lation|ling)?|fee|cargo|coverage|insurance|seguro|"
    r"hipaa|gdpr|appointment|cita|referral|document(?:s|ation)?|"
    r"what do i need|according to|seg[uú]n (?:la |el )?|"
    r"no-?show|medicare|medicaid)\b",
    re.IGNORECASE,
)


class AgentState(TypedDict):
    """State travelling between nodes. Tools add route + tool_result only."""

    question: str
    context: list[dict]
    answer: str
    route: str
    tool_result: dict
    sources_used: list[str]


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


def extract_ticket_id(question: str) -> int | None:
    """Return the first ticket/incident id mentioned in ``question``, if any."""
    match = _TICKET_ID_RE.search(question or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def extract_sku(question: str) -> str | None:
    """Return the first HealthCore SKU mentioned in ``question``, if any."""
    match = _SKU_RE.search(question or "")
    return match.group(1).upper() if match else None


def extract_inventory_name_query(question: str) -> str | None:
    """Best-effort product name fragment for stock questions without a SKU."""
    if extract_sku(question or ""):
        return None
    cleaned = _INVENTORY_KEYWORDS_RE.sub(" ", question or "")
    cleaned = re.sub(r"[¿?¡!.,;:]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def has_policy_signal(question: str) -> bool:
    """True when the question also asks about stable policy/procedure knowledge."""
    return bool(_POLICY_SIGNAL_RE.search(question or ""))


def _needs_incident_tool(text: str) -> bool:
    return (
        extract_ticket_id(text) is not None
        or bool(_TICKET_STATUS_RE.search(text))
        or bool(_INCIDENT_KEYWORDS_RE.search(text))
    )


def _needs_inventory_tool(text: str) -> bool:
    return extract_sku(text) is not None or bool(_INVENTORY_KEYWORDS_RE.search(text))


def classify_route(
    question: str,
) -> Literal[
    "refuse",
    "incidents",
    "inventory",
    "hybrid_incidents",
    "hybrid_inventory",
    "rag",
]:
    """Decide source(s) from the question alone (no user-specified source)."""
    text = (question or "").strip()
    if not text:
        return "refuse"
    policy = has_policy_signal(text)
    # Incidents before inventory: ticket ids must never be confused with stock.
    if _needs_incident_tool(text):
        return "hybrid_incidents" if policy else "incidents"
    if _needs_inventory_tool(text):
        return "hybrid_inventory" if policy else "inventory"
    return "rag"


def is_hybrid_route(route: str | None) -> bool:
    """True for routes that combine a live tool with RAG in one run."""
    return bool(route) and str(route).startswith("hybrid_")


# --- Nodes: one responsibility each ---


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


def decide_route_node(state: AgentState) -> dict:
    """Classify which source(s) the question needs: RAG, tool, or both."""
    started = time.time()
    route = "rag"
    ticket_id: int | None = None
    sku: str | None = None
    try:
        route = classify_route(state["question"])
        ticket_id = extract_ticket_id(state["question"])
        sku = extract_sku(state["question"])
        return {"route": route}
    finally:
        _record_span(
            "decide_route",
            started,
            time.time(),
            {"route": route, "ticket_id": ticket_id, "sku": sku},
        )


def retrieve_node(state: AgentState) -> dict:
    """Retrieve policy chunks for ``state['question']`` via ``retrieve()``."""
    started = time.time()
    context: list[dict] = []
    try:
        context = rag_pipeline.retrieve(state["question"])
        sources = list(state.get("sources_used") or [])
        if "rag" not in sources:
            sources = [*sources, "rag"]
        return {"context": context, "sources_used": sources}
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
                "source_kind": "rag",
                "hybrid": is_hybrid_route(state.get("route")),
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


def lookup_incident_node(state: AgentState) -> dict:
    """Call the incidents tool over MCP (the only transport); never invent state.

    ``mcp_client`` always answers with a contract payload: transport/config
    failures surface as an honest ``unavailable`` result, which the routing
    then sends to ``tool_fallback``.
    """
    started = time.time()
    tool_payload: dict = {}
    sources = list(state.get("sources_used") or [])
    try:
        ticket_id = extract_ticket_id(state["question"])
        payload = IncidentToolInput(ticket_id=ticket_id)
        result = mcp_client.lookup_incident_via_mcp(payload)
        tool_payload = result.model_dump()
        if "incidents" not in sources:
            sources = [*sources, "incidents"]
        answer = format_incident_answer(result)
        return {
            "tool_result": tool_payload,
            "sources_used": sources,
            "answer": answer if result.ok else "",
        }
    finally:
        _record_span(
            "lookup_incident",
            started,
            time.time(),
            {
                "source_kind": "incidents",
                "transport": "mcp",
                "ok": bool(tool_payload.get("ok")),
                "error": tool_payload.get("error"),
                "n_incidents": len(tool_payload.get("incidents") or []),
                "ticket_id": extract_ticket_id(state["question"]),
            },
        )


def lookup_inventory_node(state: AgentState) -> dict:
    """Call the inventory tool over MCP (the only transport); never invent stock."""
    started = time.time()
    tool_payload: dict = {}
    sources = list(state.get("sources_used") or [])
    try:
        sku = extract_sku(state["question"])
        name_query = None if sku else extract_inventory_name_query(state["question"])
        payload = InventoryToolInput(sku=sku, name_query=name_query)
        result = mcp_client.lookup_inventory_via_mcp(payload)
        tool_payload = result.model_dump()
        if "inventory" not in sources:
            sources = [*sources, "inventory"]
        answer = format_inventory_answer(result)
        return {
            "tool_result": tool_payload,
            "sources_used": sources,
            "answer": answer if result.ok else "",
        }
    finally:
        _record_span(
            "lookup_inventory",
            started,
            time.time(),
            {
                "source_kind": "inventory",
                "transport": "mcp",
                "ok": bool(tool_payload.get("ok")),
                "error": tool_payload.get("error"),
                "n_products": len(tool_payload.get("products") or []),
                "sku": extract_sku(state["question"]),
            },
        )


def _tool_facts_text(tool_result: dict, sources_used: list[str]) -> tuple[str, bool]:
    """Render the deterministic tool fact block; ``False`` when the tool failed."""
    from data.pipelines.agent_tools import (
        IncidentToolOutput,
        InventoryToolOutput,
    )

    if "inventory" in sources_used or "products" in (tool_result or {}):
        try:
            result = InventoryToolOutput.model_validate(tool_result or {})
        except Exception:
            return INVENTORY_TOOL_FALLBACK, False
        return format_inventory_answer(result), bool(result.ok)
    from data.pipelines.agent_tools import IncidentToolOutput as _IncidentOut

    try:
        result = _IncidentOut.model_validate(tool_result or {})
    except Exception:
        return INCIDENT_TOOL_FALLBACK, False
    return format_incident_answer(result), bool(result.ok)


def tool_fallback_node(state: AgentState) -> dict:
    """Honest answer when an external tool failed or found nothing."""
    started = time.time()
    answer = ""
    try:
        tool_result = state.get("tool_result") or {}
        sources = state.get("sources_used") or []
        text, _ = _tool_facts_text(tool_result, list(sources))
        answer = text
        return {"answer": answer}
    finally:
        _record_span(
            "tool_fallback",
            started,
            time.time(),
            {
                "reason": (state.get("tool_result") or {}).get("error")
                or "tool_failed",
                "answer_chars": len(answer),
            },
        )


def answer_from_tool_node(state: AgentState) -> dict:
    """Surface a successful tool payload as the final answer (no LLM invent)."""
    started = time.time()
    answer = ""
    source_kind = "incidents"
    try:
        tool_result = state.get("tool_result") or {}
        sources = state.get("sources_used") or []
        text, _ = _tool_facts_text(tool_result, list(sources))
        answer = text
        if "inventory" in sources or "products" in tool_result:
            source_kind = "inventory"
        return {"answer": answer}
    finally:
        _record_span(
            "answer_from_tool",
            started,
            time.time(),
            {"answer_chars": len(answer), "source_kind": source_kind},
        )


def synthesize_hybrid_node(state: AgentState) -> dict:
    """Combine deterministic tool facts with the LLM policy paragraph.

    The live tool block is always rendered from the typed tool payload (never
    by the model), so ticket status / stock levels cannot be dropped or
    invented; the model only writes the policy part.
    """
    started = time.time()
    answer = ""
    tool_ok = False
    try:
        tool_result = state.get("tool_result") or {}
        sources = list(state.get("sources_used") or [])
        tool_text, tool_ok = _tool_facts_text(tool_result, sources)
        policy = list(state.get("context") or [])
        if tool_ok and policy:
            policy_text = rag_pipeline.generate_answer(
                state["question"], policy
            )
            answer = f"{tool_text}\n\n{policy_text}"
        elif tool_ok:
            answer = tool_text
        elif policy:
            policy_text = rag_pipeline.generate_answer(
                state["question"], policy
            )
            fallback = str(
                tool_result.get("message")
                or (
                    INVENTORY_TOOL_FALLBACK
                    if "inventory" in sources
                    else INCIDENT_TOOL_FALLBACK
                )
            )
            answer = f"{policy_text}\n\n{fallback}"
        else:
            answer = str(
                tool_result.get("message")
                or (
                    INVENTORY_TOOL_FALLBACK
                    if "inventory" in sources
                    else INCIDENT_TOOL_FALLBACK
                )
            )
        return {"answer": answer}
    finally:
        _record_span(
            "synthesize_hybrid",
            started,
            time.time(),
            {
                "answer_chars": len(answer),
                "tool_ok": tool_ok,
                "n_policy_chunks": len(state.get("context") or []),
            },
        )


# --- Conditional edges: explicit routing, never a hardcoded straight line ---


def route_question(state: AgentState) -> Literal["refuse", "decide_route"]:
    """Blank question short-circuits to ``refuse``; otherwise decide source."""
    return "refuse" if not state["question"].strip() else "decide_route"


def route_after_decide(
    state: AgentState,
) -> Literal["lookup_incident", "lookup_inventory", "retrieve"]:
    """Send operational/hybrid questions to their API tool; policies to RAG."""
    route = state.get("route")
    if route in ("incidents", "hybrid_incidents"):
        return "lookup_incident"
    if route in ("inventory", "hybrid_inventory"):
        return "lookup_inventory"
    return "retrieve"


def route_context(
    state: AgentState,
) -> Literal["honest", "generate", "synthesize_hybrid"]:
    """Hybrid synthesizes tool facts + policy; else honest/generate as Part 1."""
    if is_hybrid_route(state.get("route")):
        return "synthesize_hybrid"
    return "honest" if not state["context"] else "generate"


def route_after_tool(
    state: AgentState,
) -> Literal["answer_from_tool", "tool_fallback", "retrieve"]:
    """Tool-only ends here; hybrid continues to RAG so the trace shows both."""
    if is_hybrid_route(state.get("route")):
        return "retrieve"
    tool_result = state.get("tool_result") or {}
    if tool_result.get("ok"):
        return "answer_from_tool"
    return "tool_fallback"


_checkpointer = MemorySaver()

_builder = StateGraph(AgentState)
_builder.add_node("receive", receive_node)
_builder.add_node("decide_route", decide_route_node)
_builder.add_node("retrieve", retrieve_node)
_builder.add_node("generate", generate_node)
_builder.add_node("refuse", refuse_node)
_builder.add_node("honest", honest_node)
_builder.add_node("lookup_incident", lookup_incident_node)
_builder.add_node("lookup_inventory", lookup_inventory_node)
_builder.add_node("tool_fallback", tool_fallback_node)
_builder.add_node("answer_from_tool", answer_from_tool_node)
_builder.add_node("synthesize_hybrid", synthesize_hybrid_node)
_builder.add_edge(START, "receive")
_builder.add_conditional_edges("receive", route_question)
_builder.add_conditional_edges("decide_route", route_after_decide)
_builder.add_conditional_edges("retrieve", route_context)
_builder.add_conditional_edges("lookup_incident", route_after_tool)
_builder.add_conditional_edges("lookup_inventory", route_after_tool)
_builder.add_edge("refuse", END)
_builder.add_edge("honest", END)
_builder.add_edge("generate", END)
_builder.add_edge("tool_fallback", END)
_builder.add_edge("answer_from_tool", END)
_builder.add_edge("synthesize_hybrid", END)

# Compiled at import time: structural errors surface on import, not in production.
graph = _builder.compile(checkpointer=_checkpointer)


def run_agent(question: str) -> dict:
    """Run the compiled graph for ``question`` and return the final state + trace id.

    Returns ``{"question": ..., "context": [...], "answer": ..., "route": ...,
    "tool_result": ..., "sources_used": [...], "trace_id": ...}``.
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
        "sources_used": [],
        "route": None,
        "spans": [],
        "error": None,
    }
    _store_trace(trace)
    token = _current_trace_id.set(trace_id)
    try:
        result = graph.invoke(
            {
                "question": question,
                "context": [],
                "answer": "",
                "route": "",
                "tool_result": {},
                "sources_used": [],
            },
            {"configurable": {"thread_id": trace_id}},
        )
        finished = time.time()
        context = result.get("context", [])
        sources_used = list(result.get("sources_used") or [])
        trace.update(
            {
                "finished_at": finished,
                "duration_ms": round((finished - started) * 1000, 2),
                "status": "success",
                "n_chunks": len(context),
                "sources": sorted(
                    {str(chunk.get("source_document", "")) for chunk in context}
                ),
                "sources_used": sources_used,
                "route": result.get("route") or None,
            }
        )
        logger.info(
            "agent_graph run %s via %s sources=%s in %.1fms",
            trace_id,
            [span["node"] for span in trace["spans"]],
            sources_used,
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
    print(f"[trace_id={outcome['trace_id']} sources={outcome.get('sources_used')}]")
