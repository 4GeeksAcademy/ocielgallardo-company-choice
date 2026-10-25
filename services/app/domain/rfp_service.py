"""Domain operations for RFP intake tickets (Postgres via SQLModel)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, col, select

from data.pipelines.rfp_intake.departments import DEPARTMENT_OWNERS, KNOWN_DEPARTMENTS
from services.app.models.rfp import DepartmentSection, RfpDocument, RfpTicket
from services.app.schemas import (
    DepartmentSectionOut,
    RfpMetadataOut,
    RfpTicketDetail,
    RfpTicketSummary,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_RFP_DIR = _REPO_ROOT / "data" / "raw" / "rfp"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_raw_dir() -> Path:
    RAW_RFP_DIR.mkdir(parents=True, exist_ok=True)
    return RAW_RFP_DIR


def create_ticket_from_upload(
    session: Session,
    *,
    pdf_bytes: bytes,
    original_filename: str,
) -> RfpTicket:
    """Persist PDF under data/raw/rfp/ and create a ticket in analyzing."""
    ticket_id = str(uuid4())
    ensure_raw_dir()
    rel_pdf = f"data/raw/rfp/{ticket_id}.pdf"
    abs_pdf = _REPO_ROOT / rel_pdf
    abs_pdf.write_bytes(pdf_bytes)

    ticket = RfpTicket(
        ticket_id=ticket_id,
        rfp_id=None,
        status="analyzing",
        raw_pdf_path=rel_pdf.replace("\\", "/"),
        ready_for_part2=False,
        handoff_payload={},
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    session.add(ticket)
    doc = RfpDocument(
        ticket_id=ticket_id,
        original_filename=original_filename,
        departments_needed=[],
        readability_metrics={},
    )
    session.add(doc)
    session.commit()
    session.refresh(ticket)
    return ticket


def get_ticket(session: Session, ticket_id: str) -> RfpTicket:
    ticket = session.exec(
        select(RfpTicket).where(RfpTicket.ticket_id == ticket_id)
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="RFP ticket not found")
    return ticket


def list_tickets(session: Session) -> list[RfpTicketSummary]:
    rows = session.exec(
        select(RfpTicket).order_by(col(RfpTicket.created_at).desc())
    ).all()
    out: list[RfpTicketSummary] = []
    for ticket in rows:
        doc = session.exec(
            select(RfpDocument).where(RfpDocument.ticket_id == ticket.ticket_id)
        ).first()
        out.append(
            RfpTicketSummary(
                ticket_id=ticket.ticket_id,
                status=ticket.status,
                created_at=ticket.created_at,
                updated_at=ticket.updated_at,
                original_filename=doc.original_filename if doc else None,
                client_name=doc.client_name if doc else None,
                ready_for_part2=ticket.ready_for_part2,
            )
        )
    return out


def ticket_detail(session: Session, ticket_id: str) -> RfpTicketDetail:
    ticket = get_ticket(session, ticket_id)
    doc = session.exec(
        select(RfpDocument).where(RfpDocument.ticket_id == ticket_id)
    ).first()
    sections = session.exec(
        select(DepartmentSection).where(DepartmentSection.ticket_id == ticket_id)
    ).all()

    metadata = None
    if doc:
        metadata = RfpMetadataOut(
            client_name=doc.client_name,
            client_country=doc.client_country,
            program_type=doc.program_type,
            covered_population=doc.covered_population,
            deadline=doc.deadline,
            budget_range=doc.budget_range,
            departments_needed=list(doc.departments_needed or []),
            flesch_kincaid_grade=doc.flesch_kincaid_grade,
            gunning_fog=doc.gunning_fog,
            flesch_reading_ease=doc.flesch_reading_ease,
            readability_metrics=dict(doc.readability_metrics or {}),
            contains_phi=bool(doc.contains_phi),
            original_filename=doc.original_filename,
        )

    departments: list[DepartmentSectionOut] = []
    for section in sections:
        eval_results = dict(section.evaluation_results or {})
        departments.append(
            DepartmentSectionOut(
                department_id=section.department_id,
                owner=DEPARTMENT_OWNERS.get(section.department_id, "Unknown"),
                key_aspects=list(section.key_aspects or []),
                open_questions=list(section.open_questions or []),
                contains_phi=bool(eval_results.get("contains_phi", False)),
            )
        )
    # Stable order matching BRIEFING
    order = {d: i for i, d in enumerate(KNOWN_DEPARTMENTS)}
    departments.sort(key=lambda d: order.get(d.department_id, 99))

    stage, can_retry = derive_pipeline_stage(
        status=ticket.status,
        last_error=ticket.last_error,
        markdown_path=ticket.markdown_path,
        department_count=len(departments),
    )

    return RfpTicketDetail(
        ticket_id=ticket.ticket_id,
        rfp_id=ticket.rfp_id,
        status=ticket.status,
        raw_pdf_path=ticket.raw_pdf_path,
        markdown_path=ticket.markdown_path,
        last_error=ticket.last_error,
        discard_reason=ticket.discard_reason,
        ready_for_part2=ticket.ready_for_part2,
        handoff_payload=dict(ticket.handoff_payload or {}),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        metadata=metadata,
        departments=departments,
        pipeline_stage=stage,
        can_retry=can_retry,
    )


def derive_pipeline_stage(
    *,
    status: str,
    last_error: str | None,
    markdown_path: str | None,
    department_count: int,
) -> tuple[str, bool]:
    """Return (pipeline_stage, can_retry) for the ticket UI progress strip."""
    if status == "intake_complete":
        return "complete", False
    if status == "discarded":
        return "discarded", False
    if last_error:
        return "failed", True
    if department_count > 0:
        return "synthesizing", False
    if markdown_path:
        return "agents", False
    return "converting", False


def prepare_ticket_retry(session: Session, ticket_id: str) -> RfpTicket:
    """Clear last_error and reset to analyzing so Celery can re-run intake."""
    ticket = get_ticket(session, ticket_id)
    if ticket.status == "intake_complete":
        raise HTTPException(
            status_code=400,
            detail="Ticket already completed; upload a new PDF instead of retrying",
        )
    if ticket.status == "discarded":
        raise HTTPException(
            status_code=400,
            detail="Discarded tickets cannot be retried; upload a corrected PDF",
        )
    if ticket.status != "analyzing":
        raise HTTPException(status_code=400, detail=f"Cannot retry status={ticket.status}")
    if not ticket.last_error:
        raise HTTPException(
            status_code=400,
            detail="Pipeline is still running; wait for completion or an error before retrying",
        )
    ticket.last_error = None
    ticket.status = "analyzing"
    ticket.ready_for_part2 = False
    ticket.updated_at = _utc_now()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket


def set_ticket_error(session: Session, ticket_id: str, error: str) -> None:
    ticket = get_ticket(session, ticket_id)
    ticket.last_error = error[:4000]
    ticket.updated_at = _utc_now()
    session.add(ticket)
    session.commit()


def update_ticket_fields(
    session: Session,
    ticket_id: str,
    **fields: Any,
) -> RfpTicket:
    ticket = get_ticket(session, ticket_id)
    for key, value in fields.items():
        if hasattr(ticket, key):
            setattr(ticket, key, value)
    ticket.updated_at = _utc_now()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket


def upsert_document(session: Session, ticket_id: str, **fields: Any) -> RfpDocument:
    doc = session.exec(
        select(RfpDocument).where(RfpDocument.ticket_id == ticket_id)
    ).first()
    if not doc:
        doc = RfpDocument(ticket_id=ticket_id)
    for key, value in fields.items():
        if hasattr(doc, key):
            setattr(doc, key, value)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


def upsert_department_section(
    session: Session,
    ticket_id: str,
    department_id: str,
    *,
    key_aspects: list[Any],
    open_questions: list[Any],
    evaluation_results: dict[str, Any] | None = None,
) -> DepartmentSection:
    section = session.exec(
        select(DepartmentSection).where(
            DepartmentSection.ticket_id == ticket_id,
            DepartmentSection.department_id == department_id,
        )
    ).first()
    if not section:
        section = DepartmentSection(
            ticket_id=ticket_id,
            department_id=department_id,
        )
    section.key_aspects = key_aspects
    section.open_questions = open_questions
    section.evaluation_results = evaluation_results or {}
    session.add(section)
    session.commit()
    session.refresh(section)
    return section
