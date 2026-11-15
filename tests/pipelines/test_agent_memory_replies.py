"""Replies to "Do you want me to remember this for next time?".

"Yes, save that for next time." used to run through the graph too and come
back as a generic greeting + "Saved to my memory.". A bare decision now gets
one clean confirmation and nothing else; "no" and "correct me" behave too.
"""

from __future__ import annotations

import pytest

from data.pipelines import agent_graph, agent_memory, memory_proposer
from data.pipelines import rag as rag_pipeline
from data.pipelines.agent_graph import bare_memory_reply, run_agent

PROPOSAL = {
    "scope": "manchester",
    "category": "procedure",
    "fact": "Manchester referrals go through the coordinator first",
    "reason": "user corrected the referral flow",
}


@pytest.fixture
def store():
    instance = agent_memory.InMemoryMemoryStore()
    agent_memory.set_store(instance)
    yield instance
    agent_memory.reset_store()


@pytest.fixture
def llm(monkeypatch):
    """Scripted generation + decision seams; records what reached them."""
    state = {"generate": [], "decisions": [], "label": "unrelated", "edited_fact": None}
    scripts: list[tuple[str, dict | None]] = [("Referrals go via the coordinator.", PROPOSAL)]

    def _generate(question, context, *, memory=None):
        state["generate"].append(question)
        return scripts.pop(0) if scripts else ("I'm here to help with HealthCore.", None)

    def _decide(proposal, message):
        state["decisions"].append(message)
        return {"label": state["label"], "edited_fact": state["edited_fact"]}

    monkeypatch.setattr(rag_pipeline, "generate_answer_with_proposal", _generate)
    monkeypatch.setattr(rag_pipeline, "retrieve", lambda q, **kw: [{"text": "ctx"}])
    monkeypatch.setattr(memory_proposer, "classify_decision", _decide)
    agent_graph._PENDING_CLARIFICATIONS.clear()
    agent_graph._LAST_INVENTORY_MISS.clear()
    return state


def _propose(session: str) -> None:
    first = run_agent("How do referrals work in Manchester now?", session_id=session)
    assert first["answer"].endswith(agent_graph.PROPOSAL_QUESTION_EN)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Yes, save that for next time.", "approve"),
        ("yes", "approve"),
        ("Save it", "approve"),
        ("Sí, guárdalo para la próxima.", "approve"),
        ("No, don't store that.", "reject"),
        ("no", "reject"),
        ("No thanks", "reject"),
        ("Don’t save it, thanks", "reject"),
        ("correct me", "correct"),
        ("Correct me, please", "correct"),
        ("corrígeme", "correct"),
        ("Yes, and what is the cancellation fee?", None),
        ("No, the fee is 30 dollars", None),
        ("Actually, the correct fact is: referrals go to the GP", None),
        ("Yes no", None),
    ],
)
def test_bare_memory_reply_classification(message, expected) -> None:
    assert bare_memory_reply(message) == expected


def test_yes_save_that_answers_only_with_a_clean_confirmation(store, llm) -> None:
    _propose("yes")
    generated_before = len(llm["generate"])

    result = run_agent("Yes, save that for next time.", session_id="yes")

    assert result["answer"] == "Got it, I saved that for next time."
    assert "I'm here to help" not in result["answer"]
    assert "Saved to my memory." not in result["answer"]
    assert len(llm["generate"]) == generated_before  # graph not run again
    assert llm["decisions"] == []  # bare "yes" needs no LLM classification
    assert [entry.fact for entry in store.list_entries()] == [PROPOSAL["fact"]]
    assert store.get_pending("yes") is None
    assert result["memory_proposal_pending"] is False


def test_no_answers_with_a_clean_rejection(store, llm) -> None:
    _propose("no")
    result = run_agent("no", session_id="no")
    assert result["answer"] == "Understood, I won't save it."
    assert store.list_entries() == []
    assert store.get_pending("no") is None
    assert any(r.action == agent_memory.ACTION_REJECTED for r in store.list_audit())


def test_correct_me_keeps_the_proposal_and_asks_for_the_right_version(store, llm) -> None:
    _propose("fix")
    asked = run_agent("correct me", session_id="fix")

    assert asked["answer"] == agent_graph.MEMORY_ASK_CORRECTION_EN
    assert asked["memory_proposal_pending"] is True
    assert store.get_pending("fix") is not None  # still open for the correction
    assert store.list_entries() == []

    llm["label"] = "edit"
    llm["edited_fact"] = "Manchester referrals go to the GP first"
    saved = run_agent("Referrals go to the GP first, not the coordinator.", session_id="fix")

    assert saved["answer"] == agent_graph.MEMORY_EDITED_EN
    assert [entry.fact for entry in store.list_entries()] == [
        "Manchester referrals go to the GP first"
    ]
    assert store.get_pending("fix") is None


def test_approval_with_another_question_still_answers_the_question(store, llm) -> None:
    _propose("mixed")
    llm["label"] = "approve"
    result = run_agent("Yes, and what is the cancellation fee?", session_id="mixed")
    assert result["answer"].startswith("I'm here to help with HealthCore.")
    assert result["answer"].endswith("Saved to my memory.")


def test_bare_yes_is_not_rewritten_as_a_product_follow_up(store, llm) -> None:
    from data.pipelines.agent_tools import INVENTORY_NOT_FOUND_MESSAGE

    agent_graph._remember_clarification("s", INVENTORY_NOT_FOUND_MESSAGE)
    assert agent_graph.resolve_follow_up("s", "Save it") == "Save it"


@pytest.mark.parametrize(
    "message",
    [
        "do you have that info in ur memory saved?",
        "What's in your memory?",
        "What do you remember?",
        "Do you have anything saved in your memory?",
    ],
)
def test_memory_recall_questions_are_detected(message) -> None:
    assert agent_graph.is_memory_recall_question(message)
    assert not agent_graph.is_memory_revoke_request(message)


@pytest.mark.parametrize(
    "message",
    [
        "I have change my mind, dont save it",
        "I have changed my mind, don't save it",
        "forget that",
        "delete it",
        "Don't save it",
        "olvídalo",
    ],
)
def test_memory_revoke_requests_are_detected(message) -> None:
    assert agent_graph.is_memory_revoke_request(message)


def test_recall_lists_saved_preferences(store, llm) -> None:
    _propose("recall")
    run_agent("Yes, save that for next time.", session_id="recall")
    generated_before = len(llm["generate"])

    result = run_agent("do you have that info in ur memory saved?", session_id="recall")

    assert result["answer"].startswith("Yes, I have this saved in memory:")
    assert PROPOSAL["fact"] in result["answer"]
    assert "don't have a persistent memory" not in result["answer"].lower()
    assert len(llm["generate"]) == generated_before
    assert result["route"] == "memory_reply"


def test_recall_when_nothing_is_saved(store, llm) -> None:
    result = run_agent("What's in your memory?", session_id="empty")
    assert result["answer"] == "I don't have anything saved in memory yet."
    assert llm["generate"] == []


def test_change_of_mind_removes_the_latest_saved_memory(store, llm) -> None:
    _propose("revoke")
    saved = run_agent("Yes, save that for next time.", session_id="revoke")
    assert saved["answer"] == "Got it, I saved that for next time."
    assert [entry.fact for entry in store.list_entries()] == [PROPOSAL["fact"]]
    generated_before = len(llm["generate"])

    result = run_agent("I have change my mind, dont save it", session_id="revoke")

    assert result["answer"] == "Understood, I removed that from memory."
    assert store.list_entries() == []
    assert any(record.action == agent_memory.ACTION_DELETED for record in store.list_audit())
    assert len(llm["generate"]) == generated_before
    assert "knowledge base" not in result["answer"].lower()


def test_revoke_with_nothing_saved_says_so(store, llm) -> None:
    result = run_agent("forget that", session_id="none")
    assert result["answer"] == "I don't have anything saved in memory to remove."
    assert llm["generate"] == []
