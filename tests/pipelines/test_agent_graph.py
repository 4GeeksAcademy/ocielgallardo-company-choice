"""Unit tests for the LangGraph support agent (Part 1 RAG + Part 2 tools).

All tests run offline: ``retrieve``, ``generate_answer``, and the MCP tool
layer are replaced with spies via ``monkeypatch`` — no Qdrant, LLM, MCP
server, or backend in CI.

Run:
    python -m pytest tests/pipelines/test_agent_graph.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Make the repo root importable when pytest is invoked from elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

import data.pipelines.agent_graph as agent_graph  # noqa: E402
import data.pipelines.rag as rag_pipeline  # noqa: E402
from data.pipelines.agent_graph import (  # noqa: E402
    AgentState,
    classify_route,
    extract_sku,
    extract_ticket_id,
    generate_node,
    get_agent_state,
    get_last_trace,
    get_trace,
    honest_node,
    is_hybrid_route,
    receive_node,
    refuse_node,
    retrieve_node,
    route_after_decide,
    route_after_tool,
    route_context,
    route_question,
    run_agent,
)
from data.pipelines.agent_tools import (  # noqa: E402
    INCIDENT_NOT_FOUND_MESSAGE,
    INCIDENT_TOOL_FALLBACK,
    INVENTORY_TOOL_FALLBACK,
    IncidentRecord,
    IncidentToolOutput,
    InventoryRecord,
    InventoryToolOutput,
)
from data.pipelines.rag import INSUFFICIENT_INFO_ANSWER  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_traces():
    agent_graph._TRACES.clear()
    yield
    agent_graph._TRACES.clear()


def _payload(text: str, source: str = "appointment-policy") -> dict:
    return {
        "company": "healthcore",
        "source_document": source,
        "section": "Cancellation",
        "language": "en",
        "chunk_index": 0,
        "text": text,
    }


def _state(**overrides) -> dict:
    base = {
        "question": "",
        "context": [],
        "answer": "",
        "route": "",
        "tool_result": {},
        "sources_used": [],
    }
    base.update(overrides)
    return base


def _combined(fn):
    """Adapt a str-returning generate spy to the answer+proposal contract."""

    def _wrapped(question, context, *, memory=None):
        return fn(question, context), None

    return _wrapped


def test_graph_is_compiled_at_import() -> None:
    assert hasattr(agent_graph.graph, "invoke")


def test_state_holds_expected_keys() -> None:
    assert set(AgentState.__annotations__) == {
        "question",
        "context",
        "answer",
        "route",
        "tool_result",
        "sources_used",
        "session_id",
        "memory_context",
        "proposal",
        "scope_decision",
        "scope_reasons",
    }


def test_nodes_never_use_monolithic_query() -> None:
    """Static guard: no node may import or call ``query()`` (it re-runs retrieval)."""
    source = Path(agent_graph.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "data.pipelines.rag":
            assert "query" not in [alias.name for alias in node.names]
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "query" not in alias.name
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id != "query"
            elif isinstance(func, ast.Attribute):
                assert func.attr != "query"


def test_receive_node_strips_question() -> None:
    out = receive_node(_state(question="  hello?  "))
    assert out == {"question": "hello?"}


def test_retrieve_node_delegates_to_retrieve_once(monkeypatch) -> None:
    calls: list[str] = []

    def _spy_retrieve(question: str, **kwargs):
        calls.append(question)
        return [_payload("ctx")]

    monkeypatch.setattr(rag_pipeline, "retrieve", _spy_retrieve)

    out = retrieve_node(_state(question="my question"))

    assert calls == ["my question"]
    assert out["context"] == [_payload("ctx")]
    assert out["sources_used"] == ["rag"]


def test_generate_node_uses_given_context_without_retrieval(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _spy_generate(question: str, context: list[dict]):
        seen["question"] = question
        seen["context"] = context
        return "Final string"

    def _forbidden_retrieve(*args, **kwargs):
        raise AssertionError("generate_node must not call retrieve()")

    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(_spy_generate))
    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden_retrieve)

    given = [_payload("already retrieved")]
    out = generate_node(_state(question="q", context=given))

    assert out == {"answer": "Final string", "proposal": {}}
    assert seen["question"] == "q"
    assert seen["context"] == given


def test_refuse_node_answers_without_retrieval_or_llm(monkeypatch) -> None:
    def _forbidden(*args, **kwargs):
        raise AssertionError(
            "refuse_node must call neither retrieve() nor generate_answer()"
        )

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(_forbidden))

    out = refuse_node(_state(question="   "))

    assert out == {"answer": INSUFFICIENT_INFO_ANSWER}


def test_honest_node_generates_from_empty_context(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _spy_generate(question: str, context: list[dict]):
        seen["question"] = question
        seen["context"] = context
        return "Honest model answer"

    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(_spy_generate))

    out = honest_node(_state(question="q"))

    assert out == {"answer": "Honest model answer", "proposal": {}}
    assert seen["context"] == []


def test_route_question() -> None:
    assert route_question(_state(question="   ")) == "refuse"
    assert route_question(_state(question="")) == "refuse"
    assert route_question(_state(question="hello?")) == "scope_check"


def test_route_after_decide() -> None:
    assert route_after_decide(_state(route="incidents")) == "lookup_incident"
    assert (
        route_after_decide(_state(route="hybrid_incidents")) == "lookup_incident"
    )
    assert route_after_decide(_state(route="inventory")) == "lookup_inventory"
    assert (
        route_after_decide(_state(route="hybrid_inventory")) == "lookup_inventory"
    )
    assert route_after_decide(_state(route="rag")) == "retrieve"


def test_route_context() -> None:
    assert route_context(_state()) == "honest"
    assert route_context(_state(context=[_payload("ctx")])) == "generate"
    assert (
        route_context(_state(route="hybrid_incidents", context=[]))
        == "synthesize_hybrid"
    )


def test_classify_routes() -> None:
    assert extract_ticket_id("status of ticket 482?") == 482
    assert extract_sku("stock of HCR-PPE-001?") == "HCR-PPE-001"
    assert classify_route("What is the status of ticket 482?") == "incidents"
    assert classify_route("Do we have stock of HCR-PPE-001?") == "inventory"
    assert (
        classify_route("Is there a charge for cancelling 12 hours in advance?")
        == "rag"
    )
    assert classify_route("   ") == "refuse"
    assert (
        classify_route(
            "According to cancellation policy, what is the status of ticket 482?"
        )
        == "hybrid_incidents"
    )
    assert is_hybrid_route("hybrid_incidents") is True
    assert is_hybrid_route("rag") is False


def test_run_agent_calls_retrieve_exactly_once(monkeypatch) -> None:
    counts = {"retrieve": 0, "generate": 0}

    def _spy_retrieve(question: str, **kwargs):
        counts["retrieve"] += 1
        return [_payload("ctx", source="insurance-coverage")]

    def _spy_generate(question: str, context: list[dict]):
        counts["generate"] += 1
        assert context == [_payload("ctx", source="insurance-coverage")]
        return "Model answer"

    monkeypatch.setattr(rag_pipeline, "retrieve", _spy_retrieve)
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(_spy_generate))

    result = run_agent("my question")

    assert counts == {"retrieve": 1, "generate": 1}
    assert result["question"] == "my question"
    assert result["answer"] == "Model answer"
    assert result["trace_id"]
    assert result["sources_used"] == ["rag"]


def test_run_agent_produces_queryable_trace(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_pipeline,
        "retrieve",
        lambda q, **kw: [_payload("ctx", source="referral-process")],
    )
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Answer text"))

    result = run_agent("trace me")
    trace = get_trace(result["trace_id"])

    assert trace is not None
    assert trace["trace_id"] == result["trace_id"]
    assert trace["status"] == "success"
    assert trace["question"] == "trace me"
    assert trace["n_chunks"] == 1
    assert trace["sources"] == ["referral-process"]
    assert trace["sources_used"] == ["rag"]
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "scope_check",
        "decide_route",
        "retrieve",
        "generate",
    ]
    assert get_last_trace()["trace_id"] == result["trace_id"]


def test_spans_carry_per_node_outputs(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_pipeline,
        "retrieve",
        lambda q, **kw: [_payload("ctx", source="referral-process")],
    )
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Answer text"))

    result = run_agent("outputs check")
    spans = {span["node"]: span for span in get_trace(result["trace_id"])["spans"]}

    assert spans["receive"]["output"] == {"question_chars": len("outputs check")}
    assert spans["decide_route"]["output"]["route"] == "rag"
    assert spans["retrieve"]["output"]["n_chunks"] == 1
    assert spans["retrieve"]["output"]["source_kind"] == "rag"


def test_run_agent_empty_question_short_circuits(monkeypatch) -> None:
    def _forbidden(*args, **kwargs):
        raise AssertionError("blank question must never reach tools/RAG")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(_forbidden))
    monkeypatch.setattr(
        agent_graph.mcp_client, "lookup_incident_via_mcp", _forbidden
    )
    monkeypatch.setattr(
        agent_graph.mcp_client, "lookup_inventory_via_mcp", _forbidden
    )

    result = run_agent("   ")

    assert result["answer"] == INSUFFICIENT_INFO_ANSWER
    assert [span["node"] for span in get_trace(result["trace_id"])["spans"]] == [
        "receive",
        "refuse",
    ]


def test_run_agent_empty_context_routes_to_honest(monkeypatch) -> None:
    monkeypatch.setattr(rag_pipeline, "retrieve", lambda q, **kw: [])
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Honest empty answer"))

    result = run_agent("unknown topic")

    assert result["answer"] == "Honest empty answer"
    trace = get_trace(result["trace_id"])
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "scope_check",
        "decide_route",
        "retrieve",
        "honest",
    ]
    assert trace["n_chunks"] == 0


def test_checkpoint_state_inspectable_after_run(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_pipeline, "retrieve", lambda q, **kw: [_payload("ctx")]
    )
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Answer text"))

    result = run_agent("inspect me")
    state = get_agent_state(result["trace_id"])

    assert state is not None
    assert state["question"] == "inspect me"
    assert state["answer"] == "Answer text"
    assert state["context"] == [_payload("ctx")]
    assert get_agent_state("nonexistent-thread") is None


def test_run_agent_records_failed_trace(monkeypatch) -> None:
    def _boom(question: str, **kwargs):
        raise RuntimeError("Qdrant down")

    monkeypatch.setattr(rag_pipeline, "retrieve", _boom)

    with pytest.raises(RuntimeError, match="Qdrant down"):
        run_agent("failing question")

    trace = get_last_trace()
    assert trace is not None
    assert trace["status"] == "error"
    assert "Qdrant down" in (trace["error"] or "")


def _incident_tool_output() -> IncidentToolOutput:
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


def test_run_agent_ticket_uses_incident_mcp_tool_not_rag(monkeypatch) -> None:
    def _forbidden(*args, **kwargs):
        raise AssertionError("ticket questions must not call retrieve()/generate")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(_forbidden))
    monkeypatch.setattr(
        agent_graph.mcp_client, "lookup_incident_via_mcp", lambda payload, **kw: _incident_tool_output()
    )

    result = run_agent("What is the status of ticket 2?")
    trace = get_trace(result["trace_id"])

    assert "open" in result["answer"]
    assert result["sources_used"] == ["incidents"]
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "scope_check",
        "decide_route",
        "lookup_incident",
        "answer_from_tool",
    ]


def test_run_agent_incident_tool_fallback_on_failure(monkeypatch) -> None:
    failed = IncidentToolOutput(
        ok=False, error="timeout", message=INCIDENT_TOOL_FALLBACK
    )
    monkeypatch.setattr(agent_graph.mcp_client, "lookup_incident_via_mcp", lambda payload, **kw: failed)

    def _forbidden(*args, **kwargs):
        raise AssertionError("failed tool must not fall through to RAG")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)

    result = run_agent("status of ticket 999?")
    trace = get_trace(result["trace_id"])

    assert result["answer"] == INCIDENT_TOOL_FALLBACK
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "scope_check",
        "decide_route",
        "lookup_incident",
        "tool_fallback",
    ]


def test_run_agent_stock_uses_inventory_mcp_tool(monkeypatch) -> None:
    tool_out = InventoryToolOutput(
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
    monkeypatch.setattr(
        agent_graph.mcp_client, "lookup_inventory_via_mcp", lambda payload, **kw: tool_out
    )

    def _forbidden(*args, **kwargs):
        raise AssertionError("stock questions must not call RAG or incident tool")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(agent_graph.mcp_client, "lookup_incident_via_mcp", _forbidden)

    result = run_agent("Do we have stock of HCR-PPE-001?")
    trace = get_trace(result["trace_id"])

    assert "1289" in result["answer"]
    assert result["sources_used"] == ["inventory"]
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "scope_check",
        "decide_route",
        "lookup_inventory",
        "answer_from_tool",
    ]


def test_run_agent_hybrid_cites_tool_facts_deterministically(
    monkeypatch,
) -> None:
    """Hybrid: tool fact block is rendered, never left to the model."""
    monkeypatch.setattr(
        agent_graph.mcp_client, "lookup_incident_via_mcp", lambda payload, **kw: _incident_tool_output()
    )
    monkeypatch.setattr(
        rag_pipeline,
        "retrieve",
        lambda q, **kw: [_payload("50 USD cancel fee")],
    )
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Policy: fee 50 USD."))

    result = run_agent(
        "According to cancellation policy, what is the status of ticket 2?"
    )
    trace = get_trace(result["trace_id"])

    assert result["route"] == "hybrid_incidents"
    assert result["sources_used"] == ["incidents", "rag"]
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "scope_check",
        "decide_route",
        "lookup_incident",
        "retrieve",
        "synthesize_hybrid",
    ]
    # Deterministic tool block first, policy paragraph after.
    assert "status=open" in result["answer"]
    assert "Policy: fee 50 USD." in result["answer"]
    assert result["answer"].index("status=open") < result["answer"].index("Policy:")


def test_run_agent_hybrid_tool_fail_still_answers_policy(monkeypatch) -> None:
    failed = IncidentToolOutput(
        ok=False, error="not_found", message=INCIDENT_NOT_FOUND_MESSAGE
    )
    monkeypatch.setattr(agent_graph.mcp_client, "lookup_incident_via_mcp", lambda payload, **kw: failed)
    monkeypatch.setattr(
        rag_pipeline, "retrieve", lambda q, **kw: [_payload("Policy only")]
    )
    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _combined(lambda q, ctx: "Policy text."))

    result = run_agent("According to policy, what is the status of ticket 999?")

    assert result["route"] == "hybrid_incidents"
    assert "Policy text." in result["answer"]
    assert INCIDENT_NOT_FOUND_MESSAGE in result["answer"]
    assert "status=open" not in result["answer"]
