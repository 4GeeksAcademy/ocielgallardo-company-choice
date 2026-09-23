"""Celery tasks for long-running reporting operations."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any

from celery import Task

from services.app.domain.task_service import record_dead_letter
from services.app.tasks.celery_app import celery_app


logger = logging.getLogger(__name__)
MAX_RETRIES = 3


def _serializable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(item) for item in value]
    return value


class ReportingTask(Task):
    """Base task with bounded retries and a durable dead-letter record."""

    max_retries = MAX_RETRIES
    autoretry_for: tuple[type[Exception], ...] = ()

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        attempt = self.request.retries + 1
        if self.request.retries >= self.max_retries:
            try:
                record_dead_letter(
                    task_id=task_id,
                    task_name=self.name,
                    attempt=attempt,
                    error_message=str(exc),
                    payload_reference=kwargs.get("month_start"),
                )
            except Exception:  # noqa: BLE001 - preserve the original task failure
                logger.exception("Unable to persist task_id=%s to DLQ", task_id)
        logger.error(
            "task_id=%s attempt=%s status=failure error=%s",
            task_id,
            attempt,
            exc,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    bind=True,
    base=ReportingTask,
    name="reporting.pipeline_run",
    max_retries=MAX_RETRIES,
)
def run_pipeline_task(
    self: ReportingTask,
    month_start: str | None = None,
) -> dict[str, Any]:
    """Run the reporting pipeline outside the FastAPI process."""
    started_at = time.perf_counter()
    attempt = self.request.retries + 1
    try:
        from data.pipelines.pipeline import (
            trigger_monthly_clinic_supply_performance_run,
        )

        resolved_month = date.fromisoformat(month_start) if month_start else None
        result = trigger_monthly_clinic_supply_performance_run(
            month_start=resolved_month
        )
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "task_id=%s attempt=%s status=success duration_ms=%.1f",
            self.request.id,
            attempt,
            duration_ms,
        )
        return _serializable(result)
    except Exception as exc:  # noqa: BLE001 - Celery owns retry/failure handling
        duration_ms = (time.perf_counter() - started_at) * 1000
        status = "retry" if self.request.retries < self.max_retries else "failure"
        logger.error(
            "task_id=%s attempt=%s status=%s duration_ms=%.1f error=%s",
            self.request.id,
            attempt,
            status,
            duration_ms,
            exc,
        )
        if self.request.retries < self.max_retries:
            countdown = 2 ** attempt
            raise self.retry(exc=exc, countdown=countdown) from exc
        raise
