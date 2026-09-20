"""Celery application shared by the API, workers, and Flower."""

from __future__ import annotations

import os

from celery import Celery


redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "healthcore",
    broker=redis_url,
    backend=redis_url,
    include=["services.app.tasks.reporting"],
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=86400,
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 3600},
    task_soft_time_limit=900,
    task_time_limit=960,
)
