"""SQLModel ORM table for append-only HealthCore telemetry events (Supabase)."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


class TelemetryEventRow(SQLModel, table=True):
    """Immutable telemetry fact row. No UPDATE/DELETE by design."""

    __tablename__ = "telemetry_events"
    __table_args__ = (
        Index("ix_telemetry_events_timestamp", "timestamp"),
        Index("ix_telemetry_events_event_type", "event_type"),
        Index(
            "ix_telemetry_events_tags",
            "tags",
            postgresql_using="gin",
        ),
    )

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
    )
    event_id: str = Field(max_length=64)
    timestamp: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=False)
    )
    event_type: str = Field(max_length=128)
    service: str = Field(default="backoffice", max_length=64)
    user_id: str = Field(max_length=128)
    session_id: Optional[str] = Field(default=None, max_length=128)
    tags: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
