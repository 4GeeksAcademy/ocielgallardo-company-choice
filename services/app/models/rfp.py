"""SQLModel tables for RFP intake tickets (PostgreSQL / Supabase).

Never store patient identifiers or PHI in these columns.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RfpTicket(SQLModel, table=True):
    """Lifecycle row for one uploaded RFP PDF (Parts 1–3 share this ticket)."""

    __tablename__ = "rfp_tickets"

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
    )
    # Public ticket identifier (same as id string for simplicity; kept explicit).
    ticket_id: str = Field(index=True, unique=True, max_length=64)
    rfp_id: Optional[str] = Field(default=None, max_length=64, index=True)
    status: str = Field(default="analyzing", max_length=64, index=True)
    raw_pdf_path: str = Field(max_length=512)
    markdown_path: Optional[str] = Field(default=None, max_length=512)
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    discard_reason: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    ready_for_part2: bool = Field(default=False)
    ready_for_part3: bool = Field(default=False)
    handoff_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    part2_handoff_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    # Part 3: append-only audit of agent/HITL actions for the ticket timeline.
    trace_events: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    # Soft pointer to RfpFinalDocument.id once synthesizer succeeds.
    final_document_id: Optional[int] = Field(default=None)
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class RfpDocument(SQLModel, table=True):
    """RFP metadata + readability metrics for one ticket (no PHI fields)."""

    __tablename__ = "rfp_documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True, unique=True, max_length=64)
    client_name: Optional[str] = Field(default=None, max_length=256)
    client_country: Optional[str] = Field(default=None, max_length=8)  # US | UK
    program_type: Optional[str] = Field(default=None, max_length=128)
    covered_population: Optional[str] = Field(default=None, max_length=128)
    deadline: Optional[str] = Field(default=None, max_length=64)
    budget_range: Optional[str] = Field(default=None, max_length=128)
    departments_needed: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    flesch_kincaid_grade: Optional[float] = Field(default=None)
    gunning_fog: Optional[float] = Field(default=None)
    flesch_reading_ease: Optional[float] = Field(default=None)
    readability_metrics: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    contains_phi: bool = Field(default=False)
    original_filename: Optional[str] = Field(default=None, max_length=256)


class DepartmentSection(SQLModel, table=True):
    """Per-department analysis slice (Part 1 fills key_aspects; later parts reuse)."""

    __tablename__ = "rfp_department_sections"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True, max_length=64)
    department_id: str = Field(max_length=64, index=True)
    key_aspects: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    open_questions: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    draft_content: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    evaluation_results: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    iteration_count: int = Field(default=0)
    needs_human_review: bool = Field(default=False)
    # pending | approved | rejected | request_changes
    approval_status: Optional[str] = Field(default=None, max_length=64)
    approver: Optional[str] = Field(default=None, max_length=128)
    approved_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    # Reject / request_changes rounds in Part 3 (cap before flagging for Sales).
    approval_round: int = Field(default=0)


class RfpFinalDocument(SQLModel, table=True):
    """Synthesized proposal after all required approvals (BRIEFING FinalDocument)."""

    __tablename__ = "rfp_final_documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True, unique=True, max_length=64)
    sections: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    currency: str = Field(default="USD", max_length=8)
    generated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    content_markdown: str = Field(default="", sa_column=Column(Text, nullable=False))
