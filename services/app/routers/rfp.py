"""RFP intake HTTP routes — thin trigger/status layer over data/pipelines/rfp_intake."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlmodel import Session

from services.app.core.database import get_db, is_inventory_db_configured
from services.app.core.deps import get_current_user
from services.app.domain import rfp_service
from services.app.models.user import UserPublic
from data.pipelines.rfp_intake.departments import KNOWN_DEPARTMENTS
from services.app.schemas import (
    RfpApprovalDecisionIn,
    RfpTicketCreated,
    RfpTicketDetail,
    RfpTicketSummary,
)

router = APIRouter(prefix="/rfp", tags=["rfp-intake"])


def _require_db() -> None:
    if not is_inventory_db_configured():
        raise HTTPException(
            status_code=503,
            detail="RFP intake requires DATABASE_URL or SUPABASE_DB_* in .env",
        )


@router.post("/tickets", response_model=RfpTicketCreated, status_code=202)
async def upload_rfp_ticket(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> JSONResponse:
    """Accept a PDF, create analyzing ticket, enqueue Celery pipeline (async)."""
    _ = current_user
    _require_db()

    filename = file.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are accepted")
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in {
        "application/pdf",
        "application/x-pdf",
        "binary/octet-stream",
        "application/octet-stream",
    }:
        raise HTTPException(status_code=400, detail="Content-Type must be application/pdf")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty PDF upload")
    if len(pdf_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF exceeds 25 MB limit")

    ticket = rfp_service.create_ticket_from_upload(
        session,
        pdf_bytes=pdf_bytes,
        original_filename=filename,
    )

    celery_task_id: str | None = None
    try:
        from services.app.tasks.rfp_intake import run_rfp_intake_task

        async_result = run_rfp_intake_task.apply_async(
            kwargs={"ticket_id": ticket.ticket_id}
        )
        celery_task_id = async_result.id
    except Exception as exc:  # noqa: BLE001 - still return ticket; surface error on row
        rfp_service.set_ticket_error(
            session,
            ticket.ticket_id,
            f"Failed to enqueue intake pipeline: {exc}",
        )

    body = RfpTicketCreated(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        celery_task_id=celery_task_id,
    )
    return JSONResponse(status_code=202, content=body.model_dump())


@router.get("/tickets", response_model=list[RfpTicketSummary])
def list_rfp_tickets(
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[RfpTicketSummary]:
    _ = current_user
    _require_db()
    return rfp_service.list_tickets(session)


@router.get("/tickets/{ticket_id}", response_model=RfpTicketDetail)
def get_rfp_ticket(
    ticket_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RfpTicketDetail:
    _ = current_user
    _require_db()
    return rfp_service.ticket_detail(session, ticket_id)


@router.post("/tickets/{ticket_id}/retry", response_model=RfpTicketCreated, status_code=202)
def retry_rfp_ticket(
    ticket_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> JSONResponse:
    """Re-enqueue intake after a mid-pipeline failure (status analyzing + last_error)."""
    _ = current_user
    _require_db()
    ticket = rfp_service.prepare_ticket_retry(session, ticket_id)

    celery_task_id: str | None = None
    try:
        from services.app.tasks.rfp_intake import run_rfp_intake_task

        async_result = run_rfp_intake_task.apply_async(
            kwargs={"ticket_id": ticket.ticket_id}
        )
        celery_task_id = async_result.id
    except Exception as exc:  # noqa: BLE001
        rfp_service.set_ticket_error(
            session,
            ticket.ticket_id,
            f"Failed to enqueue retry: {exc}",
        )

    body = RfpTicketCreated(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        celery_task_id=celery_task_id,
    )
    return JSONResponse(status_code=202, content=body.model_dump())


@router.post("/tickets/{ticket_id}/draft", response_model=RfpTicketCreated, status_code=202)
def start_rfp_drafting(
    ticket_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> JSONResponse:
    """Start Part 2 drafting from Part 1 handoff (no PDF re-ingest)."""
    _ = current_user
    _require_db()
    ticket = rfp_service.prepare_ticket_draft(session, ticket_id)

    celery_task_id: str | None = None
    try:
        from services.app.tasks.rfp_drafting import run_rfp_drafting_task

        async_result = run_rfp_drafting_task.apply_async(
            kwargs={"ticket_id": ticket.ticket_id}
        )
        celery_task_id = async_result.id
    except Exception as exc:  # noqa: BLE001
        # Keep drafting status but surface error so UI offers Retry (no infinite spinner).
        rfp_service.set_ticket_error(
            session,
            ticket.ticket_id,
            f"Failed to enqueue drafting pipeline: {exc}",
        )
        ticket = rfp_service.get_ticket(session, ticket.ticket_id)

    body = RfpTicketCreated(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        celery_task_id=celery_task_id,
    )
    return JSONResponse(status_code=202, content=body.model_dump())


@router.post(
    "/tickets/{ticket_id}/draft/retry",
    response_model=RfpTicketCreated,
    status_code=202,
)
def retry_rfp_drafting(
    ticket_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> JSONResponse:
    """Re-enqueue drafting after failure or re-run provisional sections."""
    _ = current_user
    _require_db()
    ticket = rfp_service.prepare_draft_retry(session, ticket_id)

    celery_task_id: str | None = None
    try:
        from services.app.tasks.rfp_drafting import run_rfp_drafting_task

        async_result = run_rfp_drafting_task.apply_async(
            kwargs={"ticket_id": ticket.ticket_id}
        )
        celery_task_id = async_result.id
    except Exception as exc:  # noqa: BLE001
        rfp_service.set_ticket_error(
            session,
            ticket.ticket_id,
            f"Failed to enqueue drafting retry: {exc}",
        )
        ticket = rfp_service.get_ticket(session, ticket.ticket_id)

    body = RfpTicketCreated(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        celery_task_id=celery_task_id,
    )
    return JSONResponse(status_code=202, content=body.model_dump())


@router.post(
    "/tickets/{ticket_id}/approval/start",
    response_model=RfpTicketCreated,
    status_code=202,
)
def start_rfp_approval(
    ticket_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> JSONResponse:
    """Start Part 3 HITL approval (guardrails + arbitration → first interrupt).

    Prefer Celery ``rfp.approval_run``; fall back to sync start until the first
    interrupt so the UI always gets approval rows without a worker.
    """
    _ = current_user
    _require_db()
    ticket = rfp_service.prepare_ticket_approval(session, ticket_id)

    celery_task_id: str | None = None
    try:
        from services.app.tasks.rfp_approval import run_rfp_approval_task

        async_result = run_rfp_approval_task.apply_async(
            kwargs={"ticket_id": ticket.ticket_id}
        )
        celery_task_id = async_result.id
    except Exception:
        celery_task_id = None

    if celery_task_id is None:
        try:
            from data.pipelines.rfp_intake import run_rfp_approval

            run_rfp_approval(ticket.ticket_id)
            ticket = rfp_service.get_ticket(session, ticket.ticket_id)
        except Exception as exc:  # noqa: BLE001
            rfp_service.set_ticket_error(
                session,
                ticket.ticket_id,
                f"Failed to start approval graph: {exc}",
            )
            ticket = rfp_service.get_ticket(session, ticket.ticket_id)

    body = RfpTicketCreated(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        celery_task_id=celery_task_id,
    )
    return JSONResponse(status_code=202, content=body.model_dump())


@router.post(
    "/tickets/{ticket_id}/approval/{department_id}",
    response_model=RfpTicketDetail,
)
def decide_rfp_approval(
    ticket_id: str,
    department_id: str,
    body: RfpApprovalDecisionIn,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RfpTicketDetail:
    """Resume checkpointer with one department decision (any order)."""
    _require_db()
    if department_id not in KNOWN_DEPARTMENTS:
        raise HTTPException(
            status_code=400, detail=f"Unknown department_id={department_id}"
        )

    ticket = rfp_service.get_ticket(session, ticket_id)
    if ticket.status != "waiting_for_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot record approval from status={ticket.status}",
        )

    actor = getattr(current_user, "email", None) or getattr(
        current_user, "username", None
    )
    try:
        from data.pipelines.rfp_intake import resume_rfp_approval

        resume_rfp_approval(
            ticket_id,
            department_id=department_id,
            decision=body.decision,
            actor=str(actor) if actor else None,
            note=body.note,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return rfp_service.ticket_detail(session, ticket_id)
