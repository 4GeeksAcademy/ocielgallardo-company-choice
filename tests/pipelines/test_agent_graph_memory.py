"""End-to-end memory-loop tests for the LangGraph agent (hito 26).

The graph, the store and the PHI screen are real; only the LLM seams are
scripted (``generate_answer_with_proposal``, ``propose_from_interaction``,
``classify_decision``) and the MCP/RAG transports are stubbed, so the suite
runs offline and deterministically.

Covers: non-memorable interactions (no proposal), memorable ones (proposal
inside the same answer), the approved cycle (fact visible in a later turn),
the rejected cycle (memory unchanged), default rejection on ambiguity,
PHI-blocked proposals, single-pending-per-session, tool-path self-evaluation
and memory-failure degradation.

Run:
    python -m pytest tests/pipelines/test_agent_graph_memory.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the repo root importable when pytest is invoked from elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

import data.pipelines.agent_graph as agent_graph  # noqa: E402
import data.pipelines.agent_memory as agent_memory  # noqa: E402
import data.pipelines.memory_proposer as memory_proposer  # noqa: E402
import data.pipelines.rag as rag_pipeline  # noqa: E402
from data.pipelines.agent_graph import get_trace, run_agent  # noqa: E402
from data.pipelines.agent_tools import (  # noqa: E402
    IncidentRecord,
    IncidentToolOutput,
)

SESSION = "test-session"

MANCHESTER_PROPOSAL = {
    "scope": "manchester",
    "category": "procedure",
    "fact": (
        "The internal referral process now goes through the coordinator "
        "before the specialist (changed last quarter)"
    ),
    "reason": "user corrected the referral flow",
}

NON_MEMORABLE = [
    "What was the no-show rate this week?",
    "Thanks, that answers my question.",
    "Can you translate this into English for the weekly report?",
]


def _payload(text: str, source: str = "appointment-policy") -> dict:
    return {
        "company": "healthcore",
        "source_document": source,
        "section": "Referrals",
        "language": "en",
        "chunk_index": 0,
        "text": text,
    }


def _incident_output() -> IncidentToolOutput:
    return IncidentToolOutput(
        ok=True,
        incidents=[
            IncidentRecord(
                id=2,
                title="Patient not informed",
                description="Patient not informed",
                category="patient_experience",
                status="open",
                origin="customer",
                branch="london_west",
                created_at="2024-01-17T00:00:00Z",
                updated_at="2024-01-17T00:00:00Z",
            )
        ],
    )


@pytest.fixture
def store():
    instance = agent_memory.InMemoryMemoryStore()
    agent_memory.set_store(instance)
    yield instance
    agent_memory.reset_store()


@pytest.fixture
def generate(monkeypatch):
    """Scripted single structured call: answer + optional proposal."""
    scripts: list[tuple[str, dict | None]] = []
    calls: list[dict] = []

    def _fake(question, context, *, memory=None):
        calls.append({"question": question, "context": context, "memory": memory})
        if scripts:
            return scripts.pop(0)
        return "Base answer.", None

    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _fake)
    monkeypatch.setattr(rag_pipeline, "retrieve", lambda q, **kw: [_payload("ctx")])

    class _Script:
        def push(self, answer: str, proposal: dict | None = None) -> None:
            scripts.append((answer, proposal))

        @property
        def calls(self) -> list[dict]:
            return calls

    return _Script()


@pytest.fixture
def decision(monkeypatch):
    """Scripted pending-proposal classification."""
    holder = {"label": "unrelated", "edited_fact": None}

    def _fake(proposal, message):
        return dict(holder)

    monkeypatch.setattr(memory_proposer, "classify_decision", _fake)
    return holder


@pytest.fixture
def tool_self_eval(monkeypatch):
    """Scripted self-evaluation for deterministic (tool) answers."""
    holder: dict = {"proposal": None}
    calls: list[dict] = []

    def _fake(question, answer):
        calls.append({"question": question, "answer": answer})
        return holder["proposal"]

    monkeypatch.setattr(memory_proposer, "propose_from_interaction", _fake)
    holder["calls"] = calls
    return holder


# --- Non-memorable interactions must not propose ---


@pytest.mark.parametrize("question", NON_MEMORABLE)
def test_non_memorable_interactions_propose_nothing(
    store, generate, question
) -> None:
    run_agent(question, session_id=SESSION)

    assert store.get_pending(SESSION) is None
    assert [
        record
        for record in store.list_audit()
        if record.action == agent_memory.ACTION_PROPOSED
    ] == []


def test_memorable_interactions_propose_inside_the_answer(store, generate) -> None:
    generate.push("Referrals now route through the coordinator.", MANCHESTER_PROPOSAL)

    result = run_agent(
        "Our Manchester referral process changed last quarter — what is it now?",
        session_id=SESSION,
    )

    assert result["answer"].endswith(
        agent_graph.PROPOSAL_QUESTION_EN
    )
    pending = store.get_pending(SESSION)
    assert pending is not None
    assert pending.fact == MANCHESTER_PROPOSAL["fact"]
    proposed = [
        record
        for record in store.list_audit()
        if record.action == agent_memory.ACTION_PROPOSED
    ]
    assert len(proposed) == 1
    assert proposed[0].status == agent_memory.STATUS_PENDING
    assert proposed[0].fact == MANCHESTER_PROPOSAL["fact"]


# --- Cycle 1: approved, and visible in a later interaction ---


def test_approved_cycle_is_remembered_later(store, generate, decision, monkeypatch) -> None:
    session = "approved-cycle"

    # Turn 1 — proposal inside the same answer.
    generate.push("Referrals now route through the coordinator.", MANCHESTER_PROPOSAL)
    first = run_agent(
        "In Manchester the referral process changed last quarter.",
        session_id=session,
    )
    assert first["answer"].endswith(agent_graph.PROPOSAL_QUESTION_EN)
    assert store.get_pending(session) is not None

    # Turn 2 — the user approves; the fact is consolidated into the store.
    decision["label"] = "approve"
    second = run_agent("Yes, save that for next time.", session_id=session)
    assert "Saved to my memory." in second["answer"]
    assert store.get_pending(session) is None
    assert [entry.fact for entry in store.list_entries()] == [MANCHESTER_PROPOSAL["fact"]]
    assert any(
        record.action == agent_memory.ACTION_APPROVED for record in store.list_audit()
    )

    # Turn 3 — a later interaction injects the remembered fact into the prompt.
    def _echo(question, context, *, memory=None):
        remembered = "; ".join(item["fact"] for item in (memory or []))
        return (f"Answer with memory: {remembered}" if remembered else "No memory."), None

    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _echo)
    third = run_agent(
        "How do internal referrals work in Manchester now?",
        session_id=session,
    )
    trace = get_trace(third["trace_id"])
    assert trace["memory"]["n_memory_facts"] == 1
    assert MANCHESTER_PROPOSAL["fact"] in third["answer"]


# --- Cycle 2: rejected, memory unchanged ---


def test_rejected_cycle_leaves_memory_unchanged(store, generate, decision) -> None:
    session = "rejected-cycle"
    generate.push("Referrals now route through the coordinator.", MANCHESTER_PROPOSAL)
    run_agent(
        "In Manchester the referral process changed last quarter.",
        session_id=session,
    )
    assert store.get_pending(session) is not None

    decision["label"] = "reject"
    second = run_agent("No, don't store that.", session_id=session)

    assert second["answer"].endswith(agent_graph._REJECTNOTE_EN)
    assert store.get_pending(session) is None
    assert store.list_entries() == []
    rejected = [
        record
        for record in store.list_audit()
        if record.action == agent_memory.ACTION_REJECTED
    ]
    assert len(rejected) == 1
    assert rejected[0].decision == "reject"


def test_ambiguous_reply_discards_by_default(store, generate, decision) -> None:
    session = "ambiguous-cycle"
    generate.push("Referrals now route through the coordinator.", MANCHESTER_PROPOSAL)
    run_agent(
        "In Manchester the referral process changed last quarter.",
        session_id=session,
    )

    decision["label"] = "unrelated"  # new question / silence / vagueness
    second = run_agent("What is the cancellation fee?", session_id=session)

    assert store.get_pending(session) is None
    assert store.list_entries() == []
    assert any(
        record.action == agent_memory.ACTION_DEFAULT_REJECTED
        for record in store.list_audit()
    )
    # Conversation continues normally: no memory note bolted onto the answer.
    assert second["answer"] == "Base answer."


def test_edit_stores_the_corrected_fact(store, generate, decision) -> None:
    session = "edit-cycle"
    generate.push("Referrals now route through the coordinator.", MANCHESTER_PROPOSAL)
    run_agent(
        "In Manchester the referral process changed last quarter.",
        session_id=session,
    )

    decision["label"] = "edit"
    decision["edited_fact"] = (
        "Manchester referrals go through the coordinator since October"
    )
    second = run_agent("Almost — it changed in October, not last quarter.", session_id=session)

    assert "Saved to my memory." in second["answer"]
    assert [entry.fact for entry in store.list_entries()] == [
        "Manchester referrals go through the coordinator since October"
    ]
    assert any(record.action == agent_memory.ACTION_EDITED for record in store.list_audit())


def test_only_one_pending_proposal_per_session(store, generate, decision) -> None:
    session = "single-pending"
    generate.push("Referrals now route through the coordinator.", MANCHESTER_PROPOSAL)
    run_agent(
        "In Manchester the referral process changed last quarter.",
        session_id=session,
    )
    # A second proposal cannot be created while one is open (store contract).
    assert (
        store.set_pending(
            agent_memory.make_pending(
                session_id=session, scope="austin", category="hours", fact="closes at 10pm"
            )
        )
        is False
    )

    # Resolving and proposing again in the same turn is allowed (closed first).
    decision["label"] = "approve"
    generate.push(
        "The Austin clinic now closes at 11pm on Fridays.",
        {"scope": "austin", "category": "hours", "fact": "closes at 11pm on Fridays", "reason": "correction"},
    )
    run_agent("Yes, save that. Also: the Austin clinic now closes at 11pm on Fridays.", session_id=session)

    pending = store.get_pending(session)
    assert pending is not None
    assert pending.fact == "closes at 11pm on Fridays"
    actions = [record.action for record in store.list_audit()]
    assert agent_memory.ACTION_APPROVED in actions
    assert agent_memory.ACTION_PROPOSED in actions


# --- PHI: rejected before it is ever shown ---


def test_phi_proposal_is_refused_and_never_stored(store, generate) -> None:
    session = "phi-cycle"
    generate.push(
        "Noted.",
        {
            "scope": "austin",
            "category": "incident_pattern",
            "fact": "The patient Johnson cancellation was caused by the reminder job",
            "reason": "user asked to remember it",
        },
    )

    result = run_agent(
        "Please remember that the patient Johnson cancellation was caused by the reminder job.",
        session_id=session,
    )

    assert "HIPAA" in result["answer"]
    assert "can't save that" in result["answer"]
    assert store.get_pending(session) is None
    assert store.list_entries() == []
    blocked = [
        record
        for record in store.list_audit()
        if record.action == agent_memory.ACTION_REJECTED_PHI
    ]
    assert len(blocked) == 1
    assert blocked[0].phi_reasons
    assert blocked[0].fact is None  # the PHI text is never persisted


def test_approved_pending_with_phi_is_blocked_at_write(store, generate, decision) -> None:
    session = "phi-approve-cycle"
    pending = agent_memory.make_pending(
        session_id=session,
        scope="austin",
        category="incident_pattern",
        fact="reminder job issue for patient Johnson",
    )
    # Bypass the proposal-time screen the way a tampered store would.
    assert store.set_pending(pending) is True
    decision["label"] = "approve"

    run_agent("Yes, save that.", session_id=session)

    assert store.list_entries() == []
    assert store.get_pending(session) is None
    assert any(
        record.action == agent_memory.ACTION_REJECTED_PHI
        for record in store.list_audit()
    )


# --- Language + tool paths + traces + degradation ---


def test_spanish_interaction_gets_spanish_memory_prompts(store, generate, decision) -> None:
    session = "spanish-cycle"
    generate.push(
        "Los referidos ahora pasan por el coordinador.",
        {**MANCHESTER_PROPOSAL, "fact": "En Manchester los referidos pasan por el coordinador"},
    )
    first = run_agent(
        "En Manchester el proceso de referidos cambió el trimestre pasado.",
        session_id=session,
    )
    assert first["answer"].endswith(agent_graph.PROPOSAL_QUESTION_ES)

    decision["label"] = "approve"
    second = run_agent("Sí, guárdalo para la próxima.", session_id=session)
    assert "Guardado en mi memoria." in second["answer"]


def test_tool_path_self_evaluates_with_one_structured_call(
    store, generate, tool_self_eval, monkeypatch
) -> None:
    monkeypatch.setattr(
        agent_graph.mcp_client,
        "lookup_incident_via_mcp",
        lambda payload, **kw: _incident_output(),
    )

    tool_self_eval["proposal"] = {
        "scope": "london",
        "category": "incident_pattern",
        "fact": "Ticket 2 keeps reopening because of the reschedule notifier",
        "reason": "recurring pattern reported by the user",
    }
    result = run_agent("What is the status of ticket 2?", session_id=SESSION)

    assert result["route"] == "incidents"
    assert result["answer"].endswith(agent_graph.PROPOSAL_QUESTION_EN)
    assert store.get_pending(SESSION) is not None
    assert tool_self_eval["calls"]  # exactly the self-evaluation seam was used
    assert generate.calls == []  # tool-only path never calls the RAG generator


def test_trace_records_memory_summary(store, generate) -> None:
    generate.push("Referrals now route through the coordinator.", MANCHESTER_PROPOSAL)
    result = run_agent(
        "In Manchester the referral process changed last quarter.",
        session_id=SESSION,
    )
    trace = get_trace(result["trace_id"])
    assert trace["session_id"] == SESSION
    assert trace["memory"] == {
        "n_memory_facts": 0,
        "resolution": "none",
        "proposal": "proposed",
    }


def test_memory_failure_never_breaks_the_answer(store, generate, monkeypatch) -> None:
    def _boom():
        raise agent_memory.StoreError("redis down")

    monkeypatch.setattr(agent_graph.agent_memory, "get_store", _boom)
    result = run_agent("Is there a charge for cancelling 12 hours in advance?", session_id=SESSION)
    assert result["answer"] == "Base answer."
    assert get_trace(result["trace_id"])["status"] == "success"
