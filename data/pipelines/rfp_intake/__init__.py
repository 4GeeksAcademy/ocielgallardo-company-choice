"""RFP intake pipeline — Part 1 reception & routing (dedicated graph)."""

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


__all__ = ["run_rfp_intake"]
