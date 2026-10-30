#!/usr/bin/env python3
"""Reproducible Part 3 E2E path with simulated human approvals (no UI clicks).

Seeds Part-2-shaped section drafts (Meridian / US / BAA), starts the approval
graph, resumes departments out of order (clinical before revenue), and asserts
waiting_for_approval → done + final document.

Usage (from repo root)::

    uv run python scripts/run_rfp_approval_e2e.py

Optional env:
  RFP_E2E_TICKET_ID  — fixed ticket id for checkpoint inspection
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _sections() -> dict:
    return {
        "revenue": {
            "department_id": "revenue",
            "draft_content": (
                "## Revenue Cycle\n"
                "Meridian Manufacturing (US): occupational health fees quoted in **USD** "
                "for 800 employees, 12-month term, net-30."
            ),
            "contains_phi": False,
            "evaluation_results": {
                "contains_phi": False,
                "overall_pass": True,
                "compliance": {"pass": True, "violations": []},
            },
            "key_aspects": ["USD", "800 employees", "12-month"],
            "open_questions": [],
        },
        "clinical": {
            "department_id": "clinical",
            "draft_content": (
                "## Clinical Operations\n"
                "Austin clinic staffing can cover the contracted population with "
                "sufficient capacity for on-site occupational health."
            ),
            "contains_phi": False,
            "evaluation_results": {
                "contains_phi": False,
                "overall_pass": True,
            },
            "key_aspects": ["capacity confirmed"],
            "open_questions": [],
        },
        "compliance": {
            "department_id": "compliance",
            "draft_content": (
                "## Compliance\n"
                "US client requires a Business Associate Agreement (BAA). "
                "HIPAA safeguards apply. No patient identifiers in this proposal."
            ),
            "contains_phi": False,
            "evaluation_results": {
                "contains_phi": False,
                "overall_pass": True,
            },
            "key_aspects": ["BAA", "HIPAA"],
            "open_questions": [],
        },
    }


def main() -> int:
    from data.pipelines.rfp_intake.approval_graph import (
        resume_approval_graph,
        start_approval_graph,
        thread_id_for,
    )

    ticket_id = os.getenv("RFP_E2E_TICKET_ID") or f"e2e-{uuid.uuid4()}"
    metadata = {
        "client_name": "Meridian Manufacturing",
        "client_country": "US",
        "covered_population": "800 employees",
        "program_type": "occupational health",
        "contains_phi": False,
        "deadline": "2026-12-01",
    }

    print(f"ticket_id={ticket_id}")
    print(f"thread_id={thread_id_for(ticket_id)}")

    started = start_approval_graph(
        ticket_id=ticket_id,
        metadata=metadata,
        sections=_sections(),
    )
    assert started["status"] == "waiting_for_approval", started
    assert started["interrupted"] is True
    pending = set(started["pending_interrupt_departments"])
    assert pending == {"revenue", "clinical", "compliance"}, pending
    print("start ok — parallel interrupts:", sorted(pending))

    # Approve clinical (B) while revenue (A) remains interrupted.
    after_clinical = resume_approval_graph(
        ticket_id=ticket_id,
        department_id="clinical",
        decision="approved",
        actor="e2e@healthcore.test",
        approved_at="2026-10-28T18:00:00+00:00",
    )
    assert after_clinical["approvals"]["clinical"]["approval_status"] == "approved"
    assert "revenue" in after_clinical["pending_interrupt_departments"]
    print("parallel proof ok — clinical approved, revenue still interrupted")

    after_revenue = resume_approval_graph(
        ticket_id=ticket_id,
        department_id="revenue",
        decision="approved",
        actor="e2e@healthcore.test",
        approved_at="2026-10-28T18:01:00+00:00",
    )
    assert after_revenue["approvals"]["revenue"]["approval_status"] == "approved"

    done = resume_approval_graph(
        ticket_id=ticket_id,
        department_id="compliance",
        decision="approved",
        actor="e2e@healthcore.test",
        approved_at="2026-10-28T18:02:00+00:00",
    )
    assert done["status"] == "done", done
    assert done["interrupted"] is False
    assert done["final_document"], "final document missing"
    assert done["final_document"]["currency"] == "USD"
    assert "Meridian" in done["final_document"]["content_markdown"]

    # Traceability: agent + input + output + ts on node executions
    for event in done["trace_events"]:
        assert event.get("ts"), event
        assert event.get("agent"), event
        assert "input" in event
        assert "output" in event

    summary = {
        "ticket_id": ticket_id,
        "thread_id": thread_id_for(ticket_id),
        "status": done["status"],
        "currency": done["final_document"]["currency"],
        "trace_event_count": len(done["trace_events"]),
        "approvals": {
            k: v.get("approval_status") for k, v in done["approvals"].items()
        },
    }
    print(json.dumps(summary, indent=2))
    print("E2E Part 3 simulated approvals: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
