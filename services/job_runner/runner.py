"""Nightly orchestration state for the ``job_runs`` table (Hito 22, DEV-53).

``job_runs`` records the nightly_export script lifecycle only: CSV backup export
+ pipeline trigger. It never duplicates ``reporting.pipeline_runs`` (Hito 6),
which keeps auditing extract/transform/load internals while the pipeline
subprocess runs.

State machine: ``pending -> processing -> completed | failed``. The
``processing`` row itself is the distributed lock: while one live row holds it
for ``nightly_export``, any other instance aborts. No separate lock table,
column, or flag exists by design.

This module is process-independent: it uses plain SQLAlchemy over an injected
engine and never imports FastAPI code, so the nightly script runs outside the
API process and threads.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

SCHEMA_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "pipelines" / "job_runs_schema.sql"
)

PENDING = "pending"
PROCESSING = "processing"
COMPLETED = "completed"
FAILED = "failed"

_ERROR_MAX_CHARS = 2000


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_job_runs_schema(engine: Engine) -> None:
    """Create ``job_runs`` (and its index) when missing.

    Executes ``data/pipelines/job_runs_schema.sql`` statement by statement.
    ``CREATE EXTENSION`` is Postgres-only and skipped on other dialects; the
    table DDL itself is portable because ids and timestamps are always supplied
    by this module (server defaults never need evaluation).
    """
    sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    # Drop full-line comments so statement detection is not offset by the header.
    sql = "\n".join(
        line for line in sql.splitlines() if not line.strip().startswith("--")
    )
    dialect = engine.dialect.name
    with engine.begin() as conn:
        for chunk in sql.split(";"):
            statement = chunk.strip()
            if not statement:
                continue
            if dialect != "postgresql" and statement.upper().startswith(
                "CREATE EXTENSION"
            ):
                continue
            conn.execute(text(statement))
    logger.info("job_runs schema ensured (dialect=%s)", dialect)


def create_job_run(engine: Engine, *, job_name: str, target_date: date) -> str:
    """Insert a ``pending`` run row and return its id (before any work starts)."""
    run_id = str(uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO job_runs (id, job_name, target_date, status, created_at)
                VALUES (:run_id, :job_name, :target_date, :status, :created_at)
                """
            ),
            {
                "run_id": run_id,
                "job_name": job_name,
                "target_date": target_date.isoformat(),
                "status": PENDING,
                "created_at": _utcnow(),
            },
        )
    logger.info(
        "job_runs created run_id=%s job=%s target_date=%s status=%s",
        run_id,
        job_name,
        target_date.isoformat(),
        PENDING,
    )
    return run_id


def mark_processing(engine: Engine, *, run_id: str) -> None:
    """Move a run to ``processing`` before doing any work (acquires the lock)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE job_runs
                SET status = :status, started_at = :started_at
                WHERE id = :run_id
                """
            ),
            {"run_id": run_id, "status": PROCESSING, "started_at": _utcnow()},
        )
    logger.info("job_runs run_id=%s status=%s", run_id, PROCESSING)


def mark_completed(engine: Engine, *, run_id: str) -> None:
    """Move a run to ``completed`` after export + pipeline both succeeded."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE job_runs
                SET status = :status, finished_at = :finished_at
                WHERE id = :run_id
                """
            ),
            {"run_id": run_id, "status": COMPLETED, "finished_at": _utcnow()},
        )
    logger.info("job_runs run_id=%s status=%s", run_id, COMPLETED)


def mark_failed(engine: Engine, *, run_id: str, error: str) -> None:
    """Move a run to ``failed`` with the exception message (never stays zombie)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE job_runs
                SET status = :status,
                    finished_at = :finished_at,
                    error_message = :error_message
                WHERE id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "status": FAILED,
                "finished_at": _utcnow(),
                "error_message": error[:_ERROR_MAX_CHARS],
            },
        )
    logger.info("job_runs run_id=%s status=%s", run_id, FAILED)


def has_processing_lock(engine: Engine, *, job_name: str) -> bool:
    """Return True when a live ``processing`` row holds the lock for the job."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT 1 FROM job_runs
                WHERE job_name = :job_name AND status = :status
                LIMIT 1
                """
            ),
            {"job_name": job_name, "status": PROCESSING},
        ).first()
    locked = row is not None
    if locked:
        logger.info("job_runs job=%s lock held (status=%s)", job_name, PROCESSING)
    return locked


def has_completed_for_date(
    engine: Engine, *, job_name: str, target_date: date
) -> bool:
    """Return True when ``(job_name, target_date)`` already completed once."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT 1 FROM job_runs
                WHERE job_name = :job_name
                  AND target_date = :target_date
                  AND status = :status
                LIMIT 1
                """
            ),
            {
                "job_name": job_name,
                "target_date": target_date.isoformat(),
                "status": COMPLETED,
            },
        ).first()
    return row is not None


def get_run(engine: Engine, *, run_id: str) -> dict[str, Any] | None:
    """Fetch one run row as a plain dict (observability / tests)."""
    with engine.connect() as conn:
        row = (
            conn.execute(
                text(
                    """
                    SELECT id, job_name, target_date, status,
                           started_at, finished_at, error_message, created_at
                    FROM job_runs
                    WHERE id = :run_id
                    """
                ),
                {"run_id": run_id},
            )
            .mappings()
            .first()
        )
    return dict(row) if row is not None else None
