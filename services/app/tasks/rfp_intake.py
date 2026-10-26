"""Celery task for long-running RFP intake pipeline."""

from __future__ import annotations

import logging
import time
from typing import Any

from celery import Task
from sqlmodel import Session

from services.app.core.database import get_engine
from services.app.domain import rfp_service
from services.app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
MAX_RETRIES = 3


class RfpIntakeTask(Task):
    max_retries = MAX_RETRIES
    autoretry_for: tuple[type[Exception], ...] = ()


@celery_app.task(
    bind=True,
    base=RfpIntakeTask,
    name="rfp.intake_run",
    max_retries=MAX_RETRIES,
)
def run_rfp_intake_task(self: RfpIntakeTask, ticket_id: str) -> dict[str, Any]:
    """Run ``data.pipelines.rfp_intake.run_rfp_intake`` outside the API process."""
    started = time.perf_counter()
    attempt = self.request.retries + 1
    try:
        from data.pipelines.rfp_intake import run_rfp_intake

        result = run_rfp_intake(ticket_id)
        logger.info(
            "rfp_intake task_id=%s ticket_id=%s attempt=%s status=success duration_ms=%.1f",
            self.request.id,
            ticket_id,
            attempt,
            (time.perf_counter() - started) * 1000,
        )
        return result
    except Exception as exc:  # noqa: BLE001
        try:
            with Session(get_engine()) as session:
                rfp_service.set_ticket_error(session, ticket_id, str(exc))
        except Exception:  # noqa: BLE001
            logger.exception("Unable to persist last_error for ticket_id=%s", ticket_id)

        logger.error(
            "rfp_intake task_id=%s ticket_id=%s attempt=%s error=%s",
            self.request.id,
            ticket_id,
            attempt,
            exc,
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2**self.request.retries)
        raise
