"""RFP intake + drafting pipelines — Parts 1–2 (dedicated graphs)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def run_rfp_intake(ticket_id: str) -> dict[str, Any]:
    """Load ticket, run the graph, persist status / metadata / sections / handoff."""
    from sqlmodel import Session

    from data.pipelines.rfp_intake.graph import run_intake_graph
    from services.app.core.database import get_engine
    from services.app.domain import rfp_service

    with Session(get_engine()) as session:
        ticket = rfp_service.get_ticket(session, ticket_id)
        pdf_path = ticket.raw_pdf_path

    try:
        result = run_intake_graph(ticket_id=ticket_id, pdf_path=pdf_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("rfp_intake failed ticket_id=%s", ticket_id)
        with Session(get_engine()) as session:
            rfp_service.set_ticket_error(session, ticket_id, str(exc))
        raise

    status = result.get("status") or "analyzing"
    with Session(get_engine()) as session:
        if status == "discarded":
            rfp_service.update_ticket_fields(
                session,
                ticket_id,
                status="discarded",
                markdown_path=result.get("markdown_path"),
                discard_reason=result.get("discard_reason"),
                last_error=None,
                ready_for_part2=False,
                handoff_payload={},
            )
            readability = result.get("readability") or {}
            rfp_service.upsert_document(
                session,
                ticket_id,
                flesch_kincaid_grade=readability.get("flesch_kincaid_grade"),
                gunning_fog=readability.get("gunning_fog"),
                flesch_reading_ease=readability.get("flesch_reading_ease"),
                readability_metrics=readability,
                contains_phi=bool(result.get("contains_phi")),
            )
            return {"ticket_id": ticket_id, "status": "discarded", "result": result}

        metadata = result.get("metadata") or {}
        readability = result.get("readability") or {}
        rfp_service.upsert_document(
            session,
            ticket_id,
            client_name=metadata.get("client_name"),
            client_country=metadata.get("client_country"),
            program_type=metadata.get("program_type"),
            covered_population=metadata.get("covered_population"),
            deadline=metadata.get("deadline"),
            budget_range=metadata.get("budget_range"),
            departments_needed=metadata.get("departments_needed")
            or ["revenue", "clinical", "compliance"],
            flesch_kincaid_grade=readability.get("flesch_kincaid_grade"),
            gunning_fog=readability.get("gunning_fog"),
            flesch_reading_ease=readability.get("flesch_reading_ease"),
            readability_metrics=readability,
            contains_phi=bool(result.get("contains_phi") or metadata.get("contains_phi")),
        )

        for dept_id, worker in (result.get("worker_results") or {}).items():
            rfp_service.upsert_department_section(
                session,
                ticket_id,
                dept_id,
                key_aspects=list(worker.get("key_aspects") or []),
                open_questions=list(worker.get("open_questions") or []),
                evaluation_results={"contains_phi": bool(worker.get("contains_phi"))},
            )

        handoff = result.get("handoff_payload") or {}
        rfp_service.update_ticket_fields(
            session,
            ticket_id,
            status="intake_complete",
            markdown_path=result.get("markdown_path"),
            rfp_id=f"rfp-{ticket_id[:8]}",
            last_error=None,
            discard_reason=None,
            ready_for_part2=True,
            handoff_payload=handoff,
        )

    return {
        "ticket_id": ticket_id,
        "status": "intake_complete",
        "handoff_payload": result.get("handoff_payload"),
    }


def _persist_department_draft(ticket_id: str, dept: dict[str, Any]) -> None:
    """Persist one department draft as soon as its gen/eval loop finishes."""
    from sqlmodel import Session

    from services.app.core.database import get_engine
    from services.app.domain import rfp_service

    dept_id = str(dept.get("department_id") or "")
    with Session(get_engine()) as session:
        prior = rfp_service.get_department_section(session, ticket_id, dept_id)
        rfp_service.upsert_department_section(
            session,
            ticket_id,
            dept_id,
            key_aspects=list(
                dept.get("key_aspects")
                or (prior.key_aspects if prior else [])
                or []
            ),
            open_questions=list(
                dept.get("open_questions")
                or (prior.open_questions if prior else [])
                or []
            ),
            evaluation_results={
                **(dept.get("evaluation_results") or {}),
                "contains_phi": bool(dept.get("contains_phi")),
                "eval_history": dept.get("eval_history") or [],
            },
            draft_content=dept.get("draft_content"),
            iteration_count=int(dept.get("iteration_count") or 0),
            needs_human_review=bool(dept.get("needs_human_review")),
        )
        # Move into under_evaluation once the first section has a draft.
        ticket = rfp_service.get_ticket(session, ticket_id)
        if ticket.status == "drafting":
            rfp_service.update_ticket_fields(
                session, ticket_id, status="under_evaluation"
            )


def run_rfp_drafting(ticket_id: str) -> dict[str, Any]:
    """Generate + evaluate proposal sections from intake handoff (no PDF)."""
    from sqlmodel import Session

    from data.pipelines.rfp_intake.draft_graph import run_drafting_graph
    from services.app.core.database import get_engine
    from services.app.domain import rfp_service

    with Session(get_engine()) as session:
        ticket = rfp_service.get_ticket(session, ticket_id)
        if ticket.status not in {
            "intake_complete",
            "drafting",
            "under_evaluation",
            "needs_human_review",
        }:
            raise ValueError(
                f"Ticket {ticket_id} status={ticket.status} is not eligible for drafting"
            )
        if not ticket.ready_for_part2 and ticket.status == "intake_complete":
            raise ValueError(f"Ticket {ticket_id} is not ready_for_part2")

        detail = rfp_service.ticket_detail(session, ticket_id)
        metadata: dict[str, Any] = {}
        if detail.metadata:
            metadata = detail.metadata.model_dump()
        handoff = dict(ticket.handoff_payload or {})
        sections_by_dept = {
            s.department_id: {
                "key_aspects": list(s.key_aspects or []),
                "open_questions": list(s.open_questions or []),
            }
            for s in detail.departments
        }
        rfp_service.update_ticket_fields(
            session,
            ticket_id,
            status="drafting",
            last_error=None,
            ready_for_part3=False,
        )

    try:
        result = run_drafting_graph(
            ticket_id=ticket_id,
            metadata=metadata,
            handoff_payload=handoff,
            sections_by_dept=sections_by_dept,
            on_department_done=lambda dept: _persist_department_draft(
                ticket_id, dept
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("rfp_drafting failed ticket_id=%s", ticket_id)
        with Session(get_engine()) as session:
            rfp_service.set_ticket_error(session, ticket_id, str(exc))
        raise

    with Session(get_engine()) as session:
        for dept_id, dept in (result.get("department_results") or {}).items():
            _persist_department_draft(ticket_id, dept)

        terminal = result.get("status") or "under_evaluation"
        rfp_service.update_ticket_fields(
            session,
            ticket_id,
            status=terminal,
            last_error=None,
            ready_for_part3=bool(result.get("ready_for_part3")),
            part2_handoff_payload=result.get("part2_handoff_payload") or {},
        )

    return {
        "ticket_id": ticket_id,
        "status": result.get("status"),
        "ready_for_part3": result.get("ready_for_part3"),
        "part2_handoff_payload": result.get("part2_handoff_payload"),
    }


__all__ = ["run_rfp_intake", "run_rfp_drafting"]
