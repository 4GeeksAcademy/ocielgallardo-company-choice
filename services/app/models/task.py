"""SQLModel table for final background-task failures."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class TaskDeadLetter(SQLModel, table=True):
    """Durable audit record for a task that exhausted its retries."""

    __tablename__ = "task_dead_letters"

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True),
    )
    task_id: str = Field(max_length=255, index=True)
    task_name: str = Field(max_length=255)
    attempt: int
    error_message: str = Field(sa_column=Column(Text, nullable=False))
    payload_reference: str | None = Field(default=None, max_length=255)
    failed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
