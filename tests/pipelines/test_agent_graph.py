"""Unit tests for the LangGraph knowledge assistant (agent base).

All tests run offline: ``retrieve`` and ``generate_answer`` are replaced with
spies via ``monkeypatch`` — no Qdrant, embedding API, or LLM in CI.

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
    generate_node,
    get_agent_state,
    get_last_trace,
    get_trace,
    honest_node,
    receive_node,
    refuse_node,
    retrieve_node,
    route_context,
    route_question,
    run_agent,
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


def test_graph_is_compiled_at_import() -> None:
    assert hasattr(agent_graph.graph, "invoke")


def test_state_holds_only_minimal_keys() -> None:
    assert set(AgentState.__annotations__) == {"question", "context", "answer"}


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
    out = receive_node({"question": "  hello?  ", "context": [], "answer": ""})
    assert out == {"question": "hello?"}


def test_retrieve_node_delegates_to_retrieve_once(monkeypatch) -> None:
    calls: list[str] = []

    def _spy_retrieve(question: str, **kwargs):
        calls.append(question)
        return [_payload("ctx")]

    monkeypatch.setattr(rag_pipeline, "retrieve", _spy_retrieve)

    out = retrieve_node({"question": "my question", "context": [], "answer": ""})

    assert calls == ["my question"]
    assert out == {"context": [_payload("ctx")]}


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
    out = generate_node({"question": "q", "context": given, "answer": ""})

    assert out == {"answer": "Final string"}
    assert seen["question"] == "q"
    assert seen["context"] == given


def test_refuse_node_answers_without_retrieval_or_llm(monkeypatch) -> None:
    def _forbidden(*args, **kwargs):
        raise AssertionError("refuse_node must call neither retrieve() nor generate_answer()")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer", _forbidden)

    out = refuse_node({"question": "   ", "context": [], "answer": ""})

    assert out == {"answer": INSUFFICIENT_INFO_ANSWER}


def test_honest_node_generates_from_empty_context(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _spy_generate(question: str, context: list[dict]):
        seen["question"] = question
        seen["context"] = context
        return "Honest model answer"

    monkeypatch.setattr(rag_pipeline, "generate_answer", _spy_generate)

    out = honest_node({"question": "q", "context": [], "answer": ""})

    assert out == {"answer": "Honest model answer"}
    assert seen["context"] == []  # existing empty-context path, now explicit


def test_route_question() -> None:
    assert route_question({"question": "   ", "context": [], "answer": ""}) == "refuse"
    assert route_question({"question": "", "context": [], "answer": ""}) == "refuse"
    assert (
        route_question({"question": "hello?", "context": [], "answer": ""})
        == "retrieve"
    )


def test_route_context() -> None:
    assert route_context({"question": "q", "context": [], "answer": ""}) == "honest"
    assert (
        route_context({"question": "q", "context": [_payload("ctx")], "answer": ""})
        == "generate"
    )


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

    assert counts == {"retrieve": 1, "generate": 1}  # no double retrieval
    assert result["question"] == "my question"
    assert result["answer"] == "Model answer"
    assert result["trace_id"]


def test_run_agent_produces_queryable_trace(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_pipeline, "retrieve", lambda q, **kw: [_payload("ctx", source="referral-process")]
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
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "retrieve",
        "generate",
    ]
    assert get_last_trace()["trace_id"] == result["trace_id"]


def test_spans_carry_per_node_outputs(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_pipeline, "retrieve", lambda q, **kw: [_payload("ctx", source="referral-process")]
    )
    monkeypatch.setattr(
        rag_pipeline, "generate_answer", lambda q, ctx: "Answer text"
    )

    result = run_agent("outputs check")
    spans = {span["node"]: span for span in get_trace(result["trace_id"])["spans"]}

    assert spans["receive"]["output"] == {"question_chars": len("outputs check")}
    assert spans["retrieve"]["output"] == {
        "n_chunks": 1,
        "sources": ["referral-process"],
    }
    assert spans["generate"]["output"] == {"answer_chars": len("Answer text")}


def test_run_agent_empty_question_short_circuits(monkeypatch) -> None:
    def _forbidden(*args, **kwargs):
        raise AssertionError("blank question must never reach retrieve()/generate_answer()")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer", _forbidden)

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
