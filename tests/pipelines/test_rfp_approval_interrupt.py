"""Unit tests: interruption/resume, parallel HITL, iteration limit."""

from __future__ import annotations

import uuid

import pytest

from data.pipelines.rfp_intake.approval_graph import (
    MAX_APPROVAL_ROUNDS,
    resume_approval_graph,
    start_approval_graph,
    thread_id_for,
    validate_approval_decision,
)


def _clean_sections() -> dict:
    return {
        "revenue": {
            "department_id": "revenue",
            "draft_content": "USD pricing for 800 employees. Payment net-30.",
            "contains_phi": False,
            "evaluation_results": {"contains_phi": False, "overall_pass": True},
            "key_aspects": ["USD fees"],
            "open_questions": [],
        },
        "clinical": {
            "department_id": "clinical",
            "draft_content": (
                "Clinic staffing can cover the contracted population with "
                "sufficient capacity across Austin sites."
            ),
            "contains_phi": False,
            "evaluation_results": {"contains_phi": False, "overall_pass": True},
            "key_aspects": ["capacity ok"],
            "open_questions": [],
        },
        "compliance": {
            "department_id": "compliance",
            "draft_content": (
                "Business Associate Agreement (BAA) required; HIPAA safeguards; "
                "no patient identifiers."
            ),
            "contains_phi": False,
            "evaluation_results": {"contains_phi": False, "overall_pass": True},
            "key_aspects": ["BAA"],
            "open_questions": [],
        },
    }


def _meta() -> dict:
    return {
        "client_name": "Meridian Manufacturing",
        "client_country": "US",
        "covered_population": "800 employees",
        "contains_phi": False,
        "program_type": "occupational health",
    }


@pytest.fixture()
def isolated_checkpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "data.pipelines.rfp_intake.approval_graph.CHECKPOINT_PATH",
        tmp_path / "langgraph_checkpoints.db",
    )
    monkeypatch.setattr(
        "data.pipelines.rfp_intake.approval_graph.CHECKPOINT_DIR",
        tmp_path,
    )
    return tmp_path


def test_thread_id_namespaced_by_ticket():
    assert thread_id_for("abc-123") == "rfp-abc-123"
    assert thread_id_for("abc-123", "clinical") == "rfp-abc-123:clinical"
    assert thread_id_for("t1") != thread_id_for("t2")


def test_validate_approval_decision_rejects_garbage():
    with pytest.raises(ValueError, match="Invalid decision"):
        validate_approval_decision(department_id="revenue", decision="maybe")
    with pytest.raises(ValueError, match="Invalid department"):
        validate_approval_decision(department_id="sales", decision="approved")
    assert validate_approval_decision(department_id="clinical", decision="Approved") == "approved"


def test_successful_interrupt_and_resume(isolated_checkpoints):
    ticket_id = f"test-{uuid.uuid4()}"
    started = start_approval_graph(
        ticket_id=ticket_id,
        metadata=_meta(),
        sections=_clean_sections(),
    )
    assert started["interrupted"] is True
    assert started["status"] == "waiting_for_approval"
    assert set(started["pending_interrupt_departments"]) == {
        "revenue",
        "clinical",
        "compliance",
    }
    assert started["thread_id"] == thread_id_for(ticket_id)

    # Traceability: every early node logged with input/output/ts
    agents = {e.get("agent") for e in started["trace_events"]}
    assert "auto_guardrails" in agents
    assert "arbitration" in agents
    for event in started["trace_events"]:
        assert "ts" in event
        assert "input" in event
        assert "output" in event

    mid = resume_approval_graph(
        ticket_id=ticket_id,
        department_id="revenue",
        decision="approved",
        actor="tester@healthcore.test",
        approved_at="2026-10-28T12:00:00+00:00",
    )
    assert mid["approvals"]["revenue"]["approval_status"] == "approved"
    assert mid["interrupted"] is True

    mid2 = resume_approval_graph(
        ticket_id=ticket_id,
        department_id="compliance",
        decision="approved",
        actor="tester@healthcore.test",
        approved_at="2026-10-28T12:01:00+00:00",
    )
    assert mid2["approvals"]["compliance"]["approval_status"] == "approved"

    done = resume_approval_graph(
        ticket_id=ticket_id,
        department_id="clinical",
        decision="approved",
        actor="tester@healthcore.test",
        approved_at="2026-10-28T12:02:00+00:00",
    )
    assert done["interrupted"] is False
    assert done["status"] == "done"
    assert done["final_document"] is not None
    assert "Meridian" in done["final_document"]["content_markdown"]


def test_approve_b_while_a_still_interrupted_proves_parallel(isolated_checkpoints):
    """Approve clinical while revenue remains interrupted — not serial fake-parallelism."""
    ticket_id = f"test-{uuid.uuid4()}"
    started = start_approval_graph(
        ticket_id=ticket_id,
        metadata=_meta(),
        sections=_clean_sections(),
    )
    assert "revenue" in started["pending_interrupt_departments"]
    assert "clinical" in started["pending_interrupt_departments"]

    after_b = resume_approval_graph(
        ticket_id=ticket_id,
        department_id="clinical",  # department B
        decision="approved",
        actor="marcus@healthcore.test",
        approved_at="2026-10-28T12:00:00+00:00",
    )
    assert after_b["approvals"]["clinical"]["approval_status"] == "approved"
    # Department A (revenue) still interrupted
    assert "revenue" in after_b["pending_interrupt_departments"]
    assert after_b["approvals"].get("revenue", {}).get("approval_status") != "approved"
    assert after_b["interrupted"] is True
    assert after_b["final_document"] is None
    # Join must not have run to completion
    assert after_b["status"] == "waiting_for_approval"


def test_iteration_limit_reached(isolated_checkpoints):
    ticket_id = f"test-{uuid.uuid4()}"
    start_approval_graph(
        ticket_id=ticket_id,
        metadata=_meta(),
        sections=_clean_sections(),
    )
    # Exhaust rounds on revenue with request_changes
    last = None
    for i in range(MAX_APPROVAL_ROUNDS):
        last = resume_approval_graph(
            ticket_id=ticket_id,
            department_id="revenue",
            decision="request_changes",
            actor="tom@healthcore.test",
            note=f"round {i + 1}",
        )
    assert last is not None
    assert last["approvals"]["revenue"]["approval_round"] >= MAX_APPROVAL_ROUNDS
    assert last["approvals"]["revenue"]["approval_status"] == "request_changes"
    flags = last.get("sales_flags") or []
    assert any(f.get("reason") == "approval_round_limit" for f in flags)
    # Other departments can still be approved independently
    assert "clinical" in (last.get("pending_interrupt_departments") or ["clinical"])


def test_resume_validates_before_reentry(isolated_checkpoints):
    ticket_id = f"test-{uuid.uuid4()}"
    start_approval_graph(
        ticket_id=ticket_id,
        metadata=_meta(),
        sections=_clean_sections(),
    )
    with pytest.raises(ValueError, match="Invalid decision"):
        resume_approval_graph(
            ticket_id=ticket_id,
            department_id="revenue",
            decision="ship_it",
        )
