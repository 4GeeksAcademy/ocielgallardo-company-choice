"""Agent evals: verdicts computed against stored traces, not live runs.

Each eval is a pure predicate over a trace dict (plus the final answer where the
criterion covers grounding). Golden traces live in
``tests/pipelines/fixtures/agent_traces/``; generator tests prove a fresh mocked
run satisfies the same predicates, so fixtures cannot silently rot.

Part 2 routing evals: a ticket question must use the incidents MCP tool (not
RAG), a stock question the inventory MCP tool, a policy question RAG (not a
tool), and a hybrid question both in tool-then-RAG order. An optional fallback
eval covers an unavailable incident service.

The live grounding eval needs real Qdrant + LLM credentials and is skipped
unless ``RUN_LIVE_EVALS=1``.

Run:
    python -m pytest tests/pipelines/test_agent_evals.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make the repo root importable when pytest is invoked from elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

import data.pipelines.agent_graph as agent_graph  # noqa: E402
import data.pipelines.rag as rag_pipeline  # noqa: E402
from data.pipelines.agent_graph import get_trace, run_agent  # noqa: E402
from data.pipelines.agent_tools import (  # noqa: E402
    INCIDENT_TOOL_FALLBACK,
    IncidentRecord,
    IncidentToolOutput,
    InventoryRecord,
    InventoryToolOutput,
)
from data.process.rag import load_corpus  # noqa: E402

_FIXTURES = _REPO_ROOT / "tests" / "pipelines" / "fixtures" / "agent_traces"

# Known KB fact (docs/company-knowledge-base/healthcore-appointment-policy.en.md):
# "Cancelling less than 24 hours in advance, or no-show: 50 USD (or 40 GBP …".
CANCELLATION_QUESTION = "Is there a charge for cancelling 12 hours in advance?"
TICKET_QUESTION = "What is the status of ticket 2?"
STOCK_QUESTION = "Do we have stock of HCR-PPE-001?"
HYBRID_QUESTION = (
    "According to cancellation policy, what is the status of ticket 2?"
)
TICKET_FALLBACK_QUESTION = "What is the status of ticket 99999?"


def _span_nodes(trace: dict) -> list[str]:
    return [span["node"] for span in trace["spans"]]


# --- Pure eval predicates: trace (and answer) in, violation out (None = pass) ---


def _combined(fn):
    """Adapt a str-returning generate spy to the answer+proposal contract."""

    def _wrapped(question, context, *, memory=None):
        return fn(question, context), None

    return _wrapped


def eval_routing_order(trace: dict) -> str | None:
    """Happy RAG path: receive → decide_route → retrieve → generate."""
    expected = ["receive", "decide_route", "retrieve", "generate"]
    if _span_nodes(trace) != expected:
        return f"expected {expected}, got {_span_nodes(trace)}"
    return None


def eval_blank_short_circuit(trace: dict) -> str | None:
    """Blank question must reach refuse without any retrieval or tools."""
    if _span_nodes(trace) != ["receive", "refuse"]:
        return f"expected [receive, refuse], got {_span_nodes(trace)}"
    refuse = trace["spans"][1]
    if refuse["output"].get("reason") != "blank_question":
        return f"refuse span missing reason: {refuse['output']}"
    return None


def eval_empty_context_honesty(trace: dict) -> str | None:
    """Empty retrieval must route to honest instead of forcing generate."""
    expected = ["receive", "decide_route", "retrieve", "honest"]
    if _span_nodes(trace) != expected:
        return f"expected {expected}, got {_span_nodes(trace)}"
    if trace["n_chunks"] != 0:
        return f"expected n_chunks 0, got {trace['n_chunks']}"
    return None


def eval_spans_have_outputs(trace: dict) -> str | None:
    """Every executed node must record what it produced."""
    for span in trace["spans"]:
        if not isinstance(span.get("output"), dict) or not span["output"]:
            return f"span {span.get('node')} has no output summary"
    return None


def eval_grounded_answer(
    trace: dict, answer: str, *, entity: str, source: str
) -> str | None:
    """A perfect trace with an answer ignoring KB policy data is a failure."""
    if entity not in answer:
        return f"answer missing KB entity {entity!r}: {answer[:120]!r}"
    if source not in trace.get("sources", []):
        return f"trace sources {trace.get('sources')} missing {source!r}"
    return None


def eval_routes_to_tool_not_rag(trace: dict, *, tool: str) -> str | None:
    """Operational question must use its MCP tool and skip RAG entirely."""
    node = f"lookup_{tool}"
    nodes = _span_nodes(trace)
    if node not in nodes:
        return f"expected {node} in spans, got {nodes}"
    if "retrieve" in nodes or "generate" in nodes:
        return f"tool-bound question must not call RAG, got {nodes}"
    kind = "incidents" if tool == "incident" else "inventory"
    if kind not in trace.get("sources_used", []):
        return f"sources_used missing {kind}: {trace.get('sources_used')}"
    return None


def eval_routes_to_rag_not_tool(trace: dict) -> str | None:
    """Policy question must use RAG and never a tool node."""
    nodes = _span_nodes(trace)
    if "retrieve" not in nodes:
        return f"expected retrieve in spans, got {nodes}"
    if "lookup_incident" in nodes or "lookup_inventory" in nodes:
        return f"policy question must not call tool nodes, got {nodes}"
    if "rag" not in trace.get("sources_used", []):
        return f"sources_used missing rag: {trace.get('sources_used')}"
    return None


def eval_routes_to_hybrid_tool_and_rag(trace: dict) -> str | None:
    """Hybrid run must use a tool and RAG, with the tool before RAG."""
    nodes = _span_nodes(trace)
    tool_nodes = [n for n in ("lookup_incident", "lookup_inventory") if n in nodes]
    if not tool_nodes:
        return f"hybrid expected a tool node, got {nodes}"
    if "retrieve" not in nodes or "synthesize_hybrid" not in nodes:
        return f"hybrid expected retrieve + synthesize_hybrid, got {nodes}"
    if nodes.index(tool_nodes[0]) > nodes.index("retrieve"):
        return f"tool must run before retrieve, got {nodes}"
    used = list(trace.get("sources_used") or [])
    if "rag" not in used or (
        "incidents" not in used and "inventory" not in used
    ):
        return f"sources_used must hold tool kind then rag, got {used}"
    if used.index("rag") == 0:
        return f"sources_used order must be tool then rag, got {used}"
    route = trace.get("route")
    if not str(route).startswith("hybrid_"):
        return f"expected hybrid_* route, got {route!r}"
    return None


def eval_tool_fallback_honesty(trace: dict, answer: str) -> str | None:
    """When the tool fails, the graph must take tool_fallback (no invent)."""
    nodes = _span_nodes(trace)
    if "tool_fallback" not in nodes:
        return f"expected tool_fallback in spans, got {nodes}"
    if "retrieve" in nodes:
        return f"fallback path must not call retrieve, got {nodes}"
    if "could not confirm" not in answer.lower() and "could not find" not in answer.lower():
        return f"fallback answer not honest: {answer[:120]!r}"
    return None


def _load_golden(name: str) -> tuple[dict, str]:
    case = json.loads((_FIXTURES / name).read_text(encoding="utf-8"))
    return case["trace"], case["answer"]


@pytest.fixture(autouse=True)
def _clear_traces():
    agent_graph._TRACES.clear()
    yield
    agent_graph._TRACES.clear()


# --- Evals against golden traces (no execution at all) ---


def test_eval_routing_order_on_golden_trace() -> None:
    trace, _ = _load_golden("happy.json")
    assert eval_routing_order(trace) is None
    assert eval_spans_have_outputs(trace) is None
    assert eval_routes_to_rag_not_tool(trace) is None


def test_eval_blank_short_circuit_on_golden_trace() -> None:
    trace, _ = _load_golden("blank_question.json")
    assert eval_blank_short_circuit(trace) is None


def test_eval_empty_context_honesty_on_golden_trace() -> None:
    trace, _ = _load_golden("empty_context.json")
    assert eval_empty_context_honesty(trace) is None


def test_eval_grounded_answer_on_golden_trace() -> None:
    trace, answer = _load_golden("happy.json")
    assert (
        eval_grounded_answer(trace, answer, entity="50 USD", source="appointment-policy")
        is None
    )


def test_eval_tool_not_rag_on_golden_trace() -> None:
    """Part 2: ticket question must resolve via the incidents MCP tool, not RAG."""
    trace, _ = _load_golden("ticket_tool.json")
    assert eval_routes_to_tool_not_rag(trace, tool="incident") is None
    assert eval_spans_have_outputs(trace) is None


def test_eval_rag_not_tool_on_golden_trace() -> None:
    """Part 2: policy question must resolve via RAG, not a tool node."""
    trace, _ = _load_golden("happy.json")
    assert eval_routes_to_rag_not_tool(trace) is None


def test_eval_tool_fallback_on_golden_trace() -> None:
    """Optional Part 2: API failure takes the honest fallback path."""
    trace, answer = _load_golden("tool_fallback.json")
    assert eval_tool_fallback_honesty(trace, answer) is None


def test_eval_hybrid_tool_and_rag_on_golden_trace() -> None:
    """Hybrid: one run shows both sources, tool before RAG."""
    trace, answer = _load_golden("hybrid_incident_rag.json")
    assert eval_routes_to_hybrid_tool_and_rag(trace) is None
    assert "open" in answer


# --- Generator tests: fresh mocked runs satisfy the same evals (anti-rot) ---


def _payload(text: str, source: str = "appointment-policy") -> dict:
    return {
        "company": "healthcore",
        "source_document": source,
        "section": "Cancellation",
        "language": "en",
        "chunk_index": 0,
        "text": text,
    }


def _incident_ok() -> IncidentToolOutput:
    return IncidentToolOutput(
        ok=True,
        incidents=[
            IncidentRecord(
                id=2,
                title="Patient not informed of appointment reschedule",
                description="Patient not informed of appointment reschedule",
                category="patient_experience",
                status="open",
                origin="customer",
                branch="london_west",
                created_at="2024-01-17T00:00:00Z",
                updated_at="2024-01-17T00:00:00Z",
            )
        ],
    )


def _inventory_ok() -> InventoryToolOutput:
    return InventoryToolOutput(
        ok=True,
        products=[
            InventoryRecord(
                id=1,
                name="Guantes de nitrilo (caja de 100)",
                sku="HCR-PPE-001",
                category="ppe",
                unit="box",
                country="US",
                current_stock=1289,
            )
        ],
    )


def test_generator_happy_run_passes_routing_eval(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_pipeline, "retrieve", lambda q, **kw: [_payload("ctx")]
    )
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Answer"))

    result = run_agent("hello?")
    trace = get_trace(result["trace_id"])

    assert eval_routing_order(trace) is None
    assert eval_spans_have_outputs(trace) is None
    assert eval_routes_to_rag_not_tool(trace) is None


def test_generator_blank_run_passes_short_circuit_eval(monkeypatch) -> None:
    def _forbidden(*args, **kwargs):
        raise AssertionError("blank question must never reach retrieval/generation")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(_forbidden))

    result = run_agent("   ")

    assert eval_blank_short_circuit(get_trace(result["trace_id"])) is None


def test_generator_empty_context_run_passes_honesty_eval(monkeypatch) -> None:
    monkeypatch.setattr(rag_pipeline, "retrieve", lambda q, **kw: [])
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Honest"))

    result = run_agent("unknown topic")

    assert eval_empty_context_honesty(get_trace(result["trace_id"])) is None


def test_generator_grounded_run_uses_real_corpus_chunk(monkeypatch) -> None:
    """Wiring proof: a real KB chunk flows retrieval → answer → trace sources."""
    corpus = load_corpus(_REPO_ROOT / "docs" / "company-knowledge-base")
    chunk = next(
        chunk
        for chunk in corpus
        if chunk["source_document"] == "appointment-policy" and "50 USD" in chunk["text"]
    )
    monkeypatch.setattr(rag_pipeline, "retrieve", lambda q, **kw: [chunk])
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: f"Echo: {ctx[0]['text']}"))

    result = run_agent(CANCELLATION_QUESTION)
    trace = get_trace(result["trace_id"])

    assert (
        eval_grounded_answer(
            trace, result["answer"], entity="50 USD", source="appointment-policy"
        )
        is None
    )
    assert eval_routes_to_rag_not_tool(trace) is None


def test_generator_ticket_run_passes_tool_routing_eval(monkeypatch) -> None:
    """Part 2 anti-rot: ticket question → incidents MCP tool, never RAG."""

    def _forbidden(*args, **kwargs):
        raise AssertionError("ticket question must not call retrieve/generate")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(_forbidden))
    monkeypatch.setattr(agent_graph.mcp_client, "lookup_incident_via_mcp", lambda payload, **kw: _incident_ok())

    result = run_agent(TICKET_QUESTION)
    trace = get_trace(result["trace_id"])

    assert eval_routes_to_tool_not_rag(trace, tool="incident") is None
    assert "open" in result["answer"]


def test_generator_stock_run_passes_tool_routing_eval(monkeypatch) -> None:
    """Part 2 anti-rot: stock question → inventory MCP tool, never RAG."""

    def _forbidden(*args, **kwargs):
        raise AssertionError("stock question must not call RAG or incident tool")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(agent_graph.mcp_client, "lookup_incident_via_mcp", _forbidden)
    monkeypatch.setattr(agent_graph.mcp_client, "lookup_inventory_via_mcp", lambda payload, **kw: _inventory_ok())

    result = run_agent(STOCK_QUESTION)
    trace = get_trace(result["trace_id"])

    assert eval_routes_to_tool_not_rag(trace, tool="inventory") is None
    assert "1289" in result["answer"]


def test_generator_policy_run_passes_rag_routing_eval(monkeypatch) -> None:
    """Part 2 anti-rot: policy question → RAG, never tool nodes."""
    monkeypatch.setattr(
        rag_pipeline, "retrieve", lambda q, **kw: [_payload("ctx")]
    )
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Policy answer"))

    def _forbidden_tool(*args, **kwargs):
        raise AssertionError("policy question must not call tool nodes")

    monkeypatch.setattr(agent_graph.mcp_client, "lookup_incident_via_mcp", _forbidden_tool)
    monkeypatch.setattr(agent_graph.mcp_client, "lookup_inventory_via_mcp", _forbidden_tool)

    result = run_agent(CANCELLATION_QUESTION)
    trace = get_trace(result["trace_id"])

    assert eval_routes_to_rag_not_tool(trace) is None
    assert eval_routing_order(trace) is None


def test_generator_hybrid_run_passes_both_sources_eval(monkeypatch) -> None:
    """Part 2 anti-rot: policy+ticket → tool then RAG with facts cited."""
    monkeypatch.setattr(agent_graph.mcp_client, "lookup_incident_via_mcp", lambda payload, **kw: _incident_ok())
    monkeypatch.setattr(
        rag_pipeline, "retrieve", lambda q, **kw: [_payload("fee 50 USD")]
    )
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Policy: fee 50 USD."))

    result = run_agent(HYBRID_QUESTION)
    trace = get_trace(result["trace_id"])

    assert eval_routes_to_hybrid_tool_and_rag(trace) is None
    assert "status=open" in result["answer"]
    assert "Policy: fee 50 USD." in result["answer"]


def test_generator_tool_failure_passes_fallback_eval(monkeypatch) -> None:
    """Optional Part 2: unavailable MCP → honest fallback."""
    failed = IncidentToolOutput(
        ok=False, error="timeout", message=INCIDENT_TOOL_FALLBACK
    )
    monkeypatch.setattr(agent_graph.mcp_client, "lookup_incident_via_mcp", lambda payload, **kw: failed)

    def _forbidden(*args, **kwargs):
        raise AssertionError("fallback must not call RAG")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)

    result = run_agent(TICKET_FALLBACK_QUESTION)
    trace = get_trace(result["trace_id"])

    assert eval_tool_fallback_honesty(trace, result["answer"]) is None


# --- Live grounding eval: the real acceptance criterion (skipped by default) ---


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_EVALS") != "1",
    reason="needs live Qdrant index + LLM credentials (RUN_LIVE_EVALS=1)",
)
def test_live_grounded_cancellation_answer() -> None:
    """Real question → real graph → answer must carry the KB fee facts."""
    result = run_agent(CANCELLATION_QUESTION)
    trace = get_trace(result["trace_id"])

    assert eval_routing_order(trace) is None
    assert eval_routes_to_rag_not_tool(trace) is None
    assert "50" in result["answer"]
    assert "40" in result["answer"]
    assert (
        eval_grounded_answer(
            trace, result["answer"], entity="50", source="appointment-policy"
        )
        is None
    )
