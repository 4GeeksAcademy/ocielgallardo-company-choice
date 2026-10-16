"""Agent evals: verdicts computed against stored traces, not live runs.

Each eval is a pure predicate over a trace dict (plus the final answer where the
criterion covers grounding). Golden traces live in
``tests/pipelines/fixtures/agent_traces/``; generator tests prove a fresh mocked
run satisfies the same predicates, so fixtures cannot silently rot.

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
from data.process.rag import load_corpus  # noqa: E402

_FIXTURES = _REPO_ROOT / "tests" / "pipelines" / "fixtures" / "agent_traces"

# Known KB fact (docs/company-knowledge-base/healthcore-appointment-policy.en.md):
# "Cancelling less than 24 hours in advance, or no-show: 50 USD (or 40 GBP …".
CANCELLATION_QUESTION = "Is there a charge for cancelling 12 hours in advance?"


def _span_nodes(trace: dict) -> list[str]:
    return [span["node"] for span in trace["spans"]]


# --- Pure eval predicates: trace (and answer) in, violation out (None = pass) ---


def eval_routing_order(trace: dict) -> str | None:
    """Happy path must run retrieve before generate, via receive first."""
    if _span_nodes(trace) != ["receive", "retrieve", "generate"]:
        return f"expected [receive, retrieve, generate], got {_span_nodes(trace)}"
    return None


def eval_blank_short_circuit(trace: dict) -> str | None:
    """Blank question must reach refuse without any retrieval."""
    if _span_nodes(trace) != ["receive", "refuse"]:
        return f"expected [receive, refuse], got {_span_nodes(trace)}"
    refuse = trace["spans"][1]
    if refuse["output"].get("reason") != "blank_question":
        return f"refuse span missing reason: {refuse['output']}"
    return None


def eval_empty_context_honesty(trace: dict) -> str | None:
    """Empty retrieval must route to honest instead of forcing generate."""
    if _span_nodes(trace) != ["receive", "retrieve", "honest"]:
        return f"expected [receive, retrieve, honest], got {_span_nodes(trace)}"
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


def test_generator_happy_run_passes_routing_eval(monkeypatch) -> None:
    monkeypatch.setattr(
        rag_pipeline, "retrieve", lambda q, **kw: [_payload("ctx")]
    )
    monkeypatch.setattr(rag_pipeline, "generate_answer", lambda q, ctx: "Answer")

    result = run_agent("hello?")
    trace = get_trace(result["trace_id"])

    assert eval_routing_order(trace) is None
    assert eval_spans_have_outputs(trace) is None


def test_generator_blank_run_passes_short_circuit_eval(monkeypatch) -> None:
    def _forbidden(*args, **kwargs):
        raise AssertionError("blank question must never reach retrieval/generation")

    monkeypatch.setattr(rag_pipeline, "retrieve", _forbidden)
    monkeypatch.setattr(rag_pipeline, "generate_answer", _forbidden)

    result = run_agent("   ")

    assert eval_blank_short_circuit(get_trace(result["trace_id"])) is None


def test_generator_empty_context_run_passes_honesty_eval(monkeypatch) -> None:
    monkeypatch.setattr(rag_pipeline, "retrieve", lambda q, **kw: [])
    monkeypatch.setattr(rag_pipeline, "generate_answer", lambda q, ctx: "Honest")

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
    monkeypatch.setattr(
        rag_pipeline, "generate_answer", lambda q, ctx: f"Echo: {ctx[0]['text']}"
    )

    result = run_agent(CANCELLATION_QUESTION)
    trace = get_trace(result["trace_id"])

    assert (
        eval_grounded_answer(
            trace, result["answer"], entity="50 USD", source="appointment-policy"
        )
        is None
    )


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
    assert "50" in result["answer"]
    assert "40" in result["answer"]
    assert (
        eval_grounded_answer(
            trace, result["answer"], entity="50", source="appointment-policy"
        )
        is None
    )
