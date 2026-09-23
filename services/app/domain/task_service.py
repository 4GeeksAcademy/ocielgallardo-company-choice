"""Persistence operations for background-task lifecycle records."""

from __future__ import annotations

from services.app.core.database import get_engine, init_inventory_db
from services.app.models.task import TaskDeadLetter
from sqlmodel import Session


def record_dead_letter(
    *,
    task_id: str,
    task_name: str,
    attempt: int,
    error_message: str,
    payload_reference: str | None = None,
) -> None:
    """Persist only failure metadata, never the task's full payload."""
    init_inventory_db()
    with Session(get_engine()) as session:
        session.add(
            TaskDeadLetter(
                task_id=task_id,
                task_name=task_name,
                attempt=attempt,
                error_message=error_message,
                payload_reference=payload_reference,
            )
        )
        session.commit()
