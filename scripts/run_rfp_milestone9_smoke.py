#!/usr/bin/env python3
"""Smoke Parts 1→3 against the configured Postgres DB (no UI / no Celery).

Uploads Meridian sample PDF → intake → draft → approval resumes → done.

Usage (repo root)::

    uv run python scripts/run_rfp_milestone9_smoke.py

Requires DATABASE_URL or SUPABASE_DB_* in .env. Does not need Redis/Docker
when pipelines run in-process (this script).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

MERIDIAN = (
    _REPO
    / "docs"
    / "rpf-request"
    / "rfp-requests"
    / "healthcore"
    / "healthcore-request-1-formal-meridian.pdf"
)


def main() -> int:
    if not MERIDIAN.is_file():
        print(f"MISSING PDF: {MERIDIAN}", file=sys.stderr)
        return 1

    from sqlmodel import Session

    from data.pipelines.rfp_intake import (
        resume_rfp_approval,
        run_rfp_approval,
        run_rfp_drafting,
        run_rfp_intake,
    )
    from services.app.core.database import get_engine, init_inventory_db
    from services.app.domain import rfp_service

    print("init DB tables…")
    init_inventory_db()

    pdf_bytes = MERIDIAN.read_bytes()
    with Session(get_engine()) as session:
        ticket = rfp_service.create_ticket_from_upload(
            session,
            pdf_bytes=pdf_bytes,
            original_filename=MERIDIAN.name,
        )
        ticket_id = ticket.ticket_id
    print(f"ticket_id={ticket_id} status=analyzing")

    print("Part 1 intake…")
    intake = run_rfp_intake(ticket_id)
    print(json.dumps({"part1": intake.get("status"), "ready_for_part2": True}, indent=2))
    if intake.get("status") == "discarded":
        print("FAIL: Meridian was discarded", file=sys.stderr)
        return 1

    print("Part 2 drafting…")
    draft = run_rfp_drafting(ticket_id)
    print(
        json.dumps(
            {
                "part2": draft.get("status"),
                "ready_for_part3": draft.get("ready_for_part3"),
            },
            indent=2,
        )
    )
    if not draft.get("ready_for_part3"):
        print("WARN: ready_for_part3=false — continuing if under_evaluation/needs_human_review")

    with Session(get_engine()) as session:
        rfp_service.prepare_ticket_approval(session, ticket_id)

    print("Part 3 approval start…")
    started = run_rfp_approval(ticket_id)
    print(json.dumps({"part3_start": started.get("status")}, indent=2))

    # Approve out of order: clinical → revenue → compliance (parallel proof).
    for dept in ("clinical", "revenue", "compliance"):
        print(f"approve {dept}…")
        result = resume_rfp_approval(
            ticket_id,
            department_id=dept,
            decision="approved",
            actor="smoke@healthcore.test",
            note=f"smoke approve {dept}",
        )
        print(
            json.dumps(
                {
                    "status": result.get("status"),
                    "interrupted": result.get("interrupted"),
                    dept: (result.get("approvals") or {}).get(dept, {}).get(
                        "approval_status"
                    ),
                },
                indent=2,
            )
        )

    with Session(get_engine()) as session:
        detail = rfp_service.ticket_detail(session, ticket_id)

    summary = {
        "ticket_id": ticket_id,
        "status": detail.status,
        "ready_for_part3": detail.ready_for_part3,
        "final_document_id": detail.final_document_id,
        "currency": detail.final_document.currency if detail.final_document else None,
        "markdown_chars": len(detail.final_document.content_markdown)
        if detail.final_document
        else 0,
        "approvals": {
            d.department_id: d.approval_status for d in detail.departments
        },
        "trace_events": len(detail.trace_events or []),
    }
    print(json.dumps(summary, indent=2))

    if detail.status != "done" or not detail.final_document:
        print("FAIL: expected done + final_document", file=sys.stderr)
        return 1

    out = _REPO / "data" / "process" / "rfp" / f"smoke-final-{ticket_id[:8]}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(detail.final_document.content_markdown, encoding="utf-8")
    print(f"wrote {out}")
    print("Milestone 9 smoke Parts 1→3: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
