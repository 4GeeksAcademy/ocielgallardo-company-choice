"""Focused tests for Celery submission, status mapping, and DLQ behavior."""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from services.app.routers.tasks import _public_state
from services.app.tasks import reporting
from services.app.tasks.celery_app import celery_app


def test_retry_state_is_exposed_as_pending() -> None:
    assert _public_state(SimpleNamespace(state="RETRY")) == "pending"
    assert _public_state(SimpleNamespace(state="STARTED")) == "started"
    assert _public_state(SimpleNamespace(state="REVOKED")) == "pending"


def test_reporting_task_has_three_retries_and_small_reference_payload() -> None:
    assert reporting.run_pipeline_task.max_retries == 3
    assert reporting.run_pipeline_task.name == "reporting.pipeline_run"
    assert celery_app.conf.broker_url == celery_app.conf.result_backend
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.broker_transport_options["visibility_timeout"] == 3600
    assert celery_app.conf.task_soft_time_limit == 900
    assert celery_app.conf.task_time_limit == 960


def test_dead_letter_service_receives_failure_metadata(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_record_dead_letter(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(reporting, "record_dead_letter", fake_record_dead_letter)
    task = reporting.ReportingTask()
    task.name = "reporting.pipeline_run"
    monkeypatch.setattr(
        reporting.ReportingTask,
        "request",
        property(lambda _task: SimpleNamespace(retries=3)),
    )

    task.on_failure(
        RuntimeError("database unavailable"),
        "task-123",
        (),
        {"month_start": "2026-07-01"},
        None,
    )

    assert captured == {
        "task_id": "task-123",
        "task_name": "reporting.pipeline_run",
        "attempt": 4,
        "error_message": "database unavailable",
        "payload_reference": "2026-07-01",
    }


def test_dead_letter_is_not_written_before_retries_are_exhausted(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        reporting,
        "record_dead_letter",
        lambda **kwargs: calls.append(kwargs),
    )
    task = reporting.ReportingTask()
    task.name = "reporting.pipeline_run"
    monkeypatch.setattr(
        reporting.ReportingTask,
        "request",
        property(lambda _task: SimpleNamespace(retries=1)),
    )

    task.on_failure(RuntimeError("temporary"), "task-123", (), {}, None)

    assert calls == []


def test_compose_declares_shared_redis_worker_and_flower() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "image: redis:7-alpine" in compose
    assert "--maxmemory-policy\", \"noeviction" in compose
    assert "REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}" in compose
    assert "container_name: healthcore-worker" in compose
    assert "container_name: healthcore-flower" in compose
    assert '"5555:5555"' in compose
