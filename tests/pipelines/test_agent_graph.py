"""Unit tests for the LangGraph knowledge assistant (agent + external tools).

All tests run offline: ``retrieve``, ``generate_answer``, and the incident tool
are replaced with spies via ``monkeypatch`` — no Qdrant, LLM, or TinyDB in CI.

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
import data.pipelines.agent_tools as agent_tools  # noqa: E402
import data.pipelines.rag as rag_pipeline  # noqa: E402
from data.pipelines.agent_graph import (  # noqa: E402
    AgentState,
    classify_route,
    extract_ticket_id,
    generate_node,
    get_agent_state,
    get_last_trace,
    get_trace,
    honest_node,
    receive_node,
    refuse_node,
    retrieve_node,
    route_after_decide,
    route_after_incident_tool,
    route_context,
    route_question,
    run_agent,
)
from data.pipelines.agent_tools import (  # noqa: E402
    INCIDENT_NOT_FOUND_MESSAGE,
    INCIDENT_TOOL_FALLBACK,
    IncidentRecord,
    IncidentToolOutput,
)
from data.pipelines.rag import INSUFFICIENT_INFO_ANSWER  # noqa: E402

_STATE_KEYS = {
    "question",
    "context",
    "answer",
    "route",
    "tool_result",
    "sources_used",
}


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


def _empty_state(**overrides) -> dict:
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


def test_graph_is_compiled_at_import() -> None:
    assert hasattr(agent_graph.graph, "invoke")


def test_state_holds_expected_keys() -> None:
    assert set(AgentState.__annotations__) == _STATE_KEYS


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
    out = receive_node(_empty_state(question="  hello?  "))
    assert out == {"question": "hello?"}


def test_retrieve_node_delegates_to_retrieve_once(monkeypatch) -> None:
    calls: list[str] = []

    def _spy_retrieve(question: str, **kwargs):
        calls.append(question)
        return [_payload("ctx")]

    monkeypatch.setattr(rag_pipeline, "retrieve", _spy_retrieve)

    out = retrieve_node(_empty_state(question="my question"))

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

    monkeypatch.setattr(rag_pipeline, "generate_answer", _spy_generate)
    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden_retrieve)

    given = [_payload("already retrieved")]
    out = generate_node(_empty_state(question="q", context=given))

    assert out == {"answer": "Final string"}
    assert seen["question"] == "q"
    assert seen["context"] == given


def test_refuse_node_answers_without_retrieval_or_llm(monkeypatch) -> None:
    def _forbidden(*args, **kwargs):
        raise AssertionError(
            "refuse_node must call neither retrieve() nor generate_answer()"
        )

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer", _forbidden)

    out = refuse_node(_empty_state(question="   "))

    assert out == {"answer": INSUFFICIENT_INFO_ANSWER}


def test_honest_node_generates_from_empty_context(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _spy_generate(question: str, context: list[dict]):
        seen["question"] = question
        seen["context"] = context
        return "Honest model answer"

    monkeypatch.setattr(rag_pipeline, "generate_answer", _spy_generate)

    out = honest_node(_empty_state(question="q"))

    assert out == {"answer": "Honest model answer"}
    assert seen["context"] == []


def test_route_question() -> None:
    assert route_question(_empty_state(question="   ")) == "refuse"
    assert route_question(_empty_state(question="")) == "refuse"
    assert route_question(_empty_state(question="hello?")) == "decide_route"


def test_route_after_decide() -> None:
    assert (
        route_after_decide(_empty_state(route="incidents")) == "lookup_incident"
    )
    assert route_after_decide(_empty_state(route="rag")) == "retrieve"


def test_route_context() -> None:
    assert route_context(_empty_state()) == "honest"
    assert route_context(_empty_state(context=[_payload("ctx")])) == "generate"


def test_classify_and_extract_ticket() -> None:
    assert extract_ticket_id("status of ticket 482?") == 482
    assert extract_ticket_id("Is there a cancellation fee?") is None
    assert classify_route("What is the status of ticket 482?") == "incidents"
    assert classify_route("Is there a charge for cancelling 12 hours in advance?") == "rag"
    assert classify_route("   ") == "refuse"


def test_classify_hybrid_when_ticket_and_policy() -> None:
    from data.pipelines.agent_graph import has_policy_signal

    q = (
        "According to our cancellation policy, what is the status of ticket 482 "
        "and does a no-show fee apply?"
    )
    assert has_policy_signal(q) is True
    assert classify_route(q) == "hybrid_incidents"
    assert classify_route("What is the status of ticket 482?") == "incidents"
    assert (
        classify_route("Do we have stock of HCR-PPE-001 per supply policy?")
        == "hybrid_inventory"
    )
    assert classify_route("Do we have stock of HCR-PPE-001?") == "inventory"


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
    monkeypatch.setattr(rag_pipeline, "generate_answer", _spy_generate)

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
    monkeypatch.setattr(
        rag_pipeline, "generate_answer", lambda q, ctx: "Answer text"
    )

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
    monkeypatch.setattr(
        rag_pipeline, "generate_answer", lambda q, ctx: "Answer text"
    )

    result = run_agent("outputs check")
    spans = {span["node"]: span for span in get_trace(result["trace_id"])["spans"]}

    assert spans["receive"]["output"] == {"question_chars": len("outputs check")}
    assert spans["decide_route"]["output"]["route"] == "rag"
    assert spans["retrieve"]["output"]["n_chunks"] == 1
    assert spans["retrieve"]["output"]["sources"] == ["referral-process"]
    assert spans["retrieve"]["output"]["source_kind"] == "rag"
    assert spans["generate"]["output"] == {"answer_chars": len("Answer text")}


def test_run_agent_empty_question_short_circuits(monkeypatch) -> None:
    def _forbidden(*args, **kwargs):
        raise AssertionError(
            "blank question must never reach retrieve()/generate_answer()/tools"
        )

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer", _forbidden)
    monkeypatch.setattr(agent_tools, "lookup_incident", _forbidden)

    result = run_agent("   ")

    assert result["answer"] == INSUFFICIENT_INFO_ANSWER
    assert [span["node"] for span in get_trace(result["trace_id"])["spans"]] == [
        "receive",
        "refuse",
    ]


def test_run_agent_empty_context_routes_to_honest(monkeypatch) -> None:
    monkeypatch.setattr(rag_pipeline, "retrieve", lambda q, **kw: [])
    monkeypatch.setattr(
        rag_pipeline, "generate_answer", lambda q, ctx: "Honest empty answer"
    )

    result = run_agent("unknown topic")

    assert result["answer"] == "Honest empty answer"
    trace = get_trace(result["trace_id"])
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "decide_route",
        "retrieve",
        "honest",
    ]
    assert trace["n_chunks"] == 0


def test_checkpoint_state_inspectable_after_run(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_pipeline, "retrieve", lambda q, **kw: [_payload("ctx")]
    )
    monkeypatch.setattr(
        rag_pipeline, "generate_answer", lambda q, ctx: "Answer text"
    )

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


def test_run_agent_ticket_question_uses_incident_tool_not_rag(monkeypatch) -> None:
    def _forbidden_retrieve(*args, **kwargs):
        raise AssertionError("ticket questions must not call retrieve()")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden_retrieve)
    monkeypatch.setattr(
        rag_pipeline,
        "generate_answer",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no LLM on tool path")),
    )

    tool_out = IncidentToolOutput(
        ok=True,
        incidents=[
            IncidentRecord(
                id=482,
                title="Printer offline",
                description="Front desk printer",
                category="it_system",
                status="in_progress",
                origin="branch",
                branch="austin_north",
                created_at="2026-01-10T12:00:00Z",
                updated_at="2026-01-11T09:30:00Z",
            )
        ],
    )
    monkeypatch.setattr(agent_tools, "lookup_incident", lambda payload, **kw: tool_out)
    # lookup_incident is imported into agent_graph namespace at import time
    monkeypatch.setattr(agent_graph, "lookup_incident", lambda payload, **kw: tool_out)

    result = run_agent("What is the status of ticket 482?")
    trace = get_trace(result["trace_id"])

    assert "in_progress" in result["answer"]
    assert "482" in result["answer"]
    assert result["sources_used"] == ["incidents"]
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "decide_route",
        "lookup_incident",
        "answer_from_tool",
    ]
    assert "retrieve" not in [span["node"] for span in trace["spans"]]
    assert trace["sources_used"] == ["incidents"]


def test_run_agent_incident_tool_fallback_on_failure(monkeypatch) -> None:
    def _forbidden_retrieve(*args, **kwargs):
        raise AssertionError("failed tool must not fall through to RAG")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden_retrieve)

    failed = IncidentToolOutput(
        ok=False, error="timeout", message=INCIDENT_TOOL_FALLBACK
    )
    monkeypatch.setattr(agent_graph, "lookup_incident", lambda payload, **kw: failed)

    result = run_agent("status of ticket 999?")
    trace = get_trace(result["trace_id"])

    assert result["answer"] == INCIDENT_TOOL_FALLBACK
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "decide_route",
        "lookup_incident",
        "tool_fallback",
    ]


def test_run_agent_incident_not_found_is_honest(monkeypatch) -> None:
    failed = IncidentToolOutput(
        ok=False, error="not_found", message=INCIDENT_NOT_FOUND_MESSAGE
    )
    monkeypatch.setattr(agent_graph, "lookup_incident", lambda payload, **kw: failed)

    result = run_agent("estado del ticket 404?")

    assert result["answer"] == INCIDENT_NOT_FOUND_MESSAGE
    assert route_after_incident_tool(
        _empty_state(tool_result=failed.model_dump())
    ) == "tool_fallback"


def test_run_agent_hybrid_ticket_policy_uses_tool_then_rag(monkeypatch) -> None:
    """Hybrid: live incident tool runs first, then RAG; trace shows both in order."""
    tool_out = IncidentToolOutput(
        ok=True,
        incidents=[
            IncidentRecord(
                id=482,
                title="Printer offline",
                description="Front desk printer",
                category="it_system",
                status="in_progress",
                origin="branch",
                branch="austin_north",
                created_at="2026-01-10T12:00:00Z",
                updated_at="2026-01-11T09:30:00Z",
            )
        ],
    )
    monkeypatch.setattr(agent_graph, "lookup_incident", lambda payload, **kw: tool_out)
    monkeypatch.setattr(
        rag_pipeline,
        "retrieve",
        lambda q, **kw: [_payload("Cancel fee 50 USD", source="appointment-policy")],
    )
    monkeypatch.setattr(
        rag_pipeline,
        "generate_answer",
        lambda q, ctx: (
            f"Hybrid: status from tool={ctx[0]['text'][:40]}; "
            f"policy={ctx[1]['text'] if len(ctx) > 1 else ''}"
        ),
    )

    question = (
        "According to cancellation policy, what is the status of ticket 482?"
    )
    result = run_agent(question)
    trace = get_trace(result["trace_id"])
    nodes = [span["node"] for span in trace["spans"]]

    assert result["route"] == "hybrid_incidents"
    assert result["sources_used"] == ["incidents", "rag"]
    assert nodes == [
        "receive",
        "decide_route",
        "lookup_incident",
        "retrieve",
        "generate",
    ]
    assert "in_progress" in result["answer"] or "482" in result["answer"]
    assert trace["sources_used"] == ["incidents", "rag"]
    assert trace["spans"][2]["output"]["source_kind"] == "incidents"
    assert trace["spans"][3]["output"]["source_kind"] == "rag"
    assert trace["spans"][3]["output"].get("hybrid") is True


def test_run_agent_hybrid_tool_fail_still_runs_rag(monkeypatch) -> None:
    """Hybrid must not invent ticket state when the tool fails; RAG still runs."""
    failed = IncidentToolOutput(
        ok=False, error="timeout", message=INCIDENT_TOOL_FALLBACK
    )
    monkeypatch.setattr(agent_graph, "lookup_incident", lambda payload, **kw: failed)
    monkeypatch.setattr(
        rag_pipeline,
        "retrieve",
        lambda q, **kw: [_payload("Policy only", source="appointment-policy")],
    )

    def _spy_generate(question: str, context: list[dict]) -> str:
        assert context, "hybrid should keep a tool honesty chunk in context"
        assert context[0]["source_document"] == agent_graph.LIVE_TOOL_SOURCE_INCIDENT
        assert "could not confirm" in context[0]["text"].lower()
        return f"Policy path: {context[-1]['text']}"

    monkeypatch.setattr(rag_pipeline, "generate_answer", _spy_generate)

    result = run_agent(
        "According to policy, what is the status of ticket 999?"
    )
    trace = get_trace(result["trace_id"])

    assert result["route"] == "hybrid_incidents"
    assert result["sources_used"] == ["incidents", "rag"]
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "decide_route",
        "lookup_incident",
        "retrieve",
        "generate",
    ]
    # Tool failed: answer comes from generate spy, never a fabricated ticket status.
    assert result["answer"].startswith("Policy path:")
    assert "in_progress" not in result["answer"].lower()


def test_run_agent_stock_question_uses_inventory_tool_not_rag(monkeypatch) -> None:
    from data.pipelines.agent_tools import InventoryRecord, InventoryToolOutput

    def _forbidden_retrieve(*args, **kwargs):
        raise AssertionError("stock questions must not call retrieve()")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden_retrieve)
    monkeypatch.setattr(
        agent_graph,
        "lookup_incident",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("stock questions must not call incident tool")
        ),
    )

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
                current_stock=55,
            )
        ],
    )
    monkeypatch.setattr(
        agent_graph, "lookup_inventory", lambda payload, **kw: tool_out
    )

    result = run_agent("Do we have stock of HCR-PPE-001?")
    trace = get_trace(result["trace_id"])

    assert "55" in result["answer"]
    assert "HCR-PPE-001" in result["answer"]
    assert result["sources_used"] == ["inventory"]
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "decide_route",
        "lookup_inventory",
        "answer_from_tool",
    ]
    assert classify_route("Do we have stock of HCR-PPE-001?") == "inventory"
