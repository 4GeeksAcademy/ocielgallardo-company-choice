"""Celery task: Part 3 RFP approval graph start (runs until first HITL interrupt)."""

from __future__ import annotations

import logging

from services.app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="rfp.approval_run",
    bind=True,
    max_retries=1,
    acks_late=True,
)
def run_rfp_approval_task(self, ticket_id: str) -> dict:
    """Start approval graph for ticket_id; persists waiting_for_approval + interrupts."""
    from data.pipelines.rfp_intake import run_rfp_approval

    logger.info("rfp.approval_run start ticket_id=%s task_id=%s", ticket_id, self.request.id)
    result = run_rfp_approval(ticket_id)
    logger.info(
        "rfp.approval_run done ticket_id=%s status=%s interrupted=%s",
        ticket_id,
        result.get("status"),
        result.get("interrupted"),
    )
    return result
