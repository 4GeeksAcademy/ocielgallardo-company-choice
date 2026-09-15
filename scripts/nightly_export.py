"""Nightly telemetry export + pipeline trigger (Hito 22, Ticket #DEV-53).

Standalone process — run from the repo root with::

    python scripts/nightly_export.py

It never runs inside the FastAPI process: no APScheduler, no lifespan hooks,
no API imports. Only stdlib + SQLAlchemy + ``services.job_runner``.

Schedule (OS crontab on the host, or a dedicated scheduler container in
production — never the API process)::

    0 2 * * * cd /opt/healthcore && /usr/bin/python scripts/nightly_export.py >> /var/log/healthcore/nightly_export.log 2>&1

Flow for the target date (``TARGET_DATE=YYYY-MM-DD`` overrides the default,
which is yesterday in UTC)::

    1. silent abort (exit 0) when a ``processing`` lock row exists
    2. silent skip (exit 0) when (job_name, target_date) already completed
    3. insert ``pending`` -> mark ``processing`` -> export CSV (skipped when the
       file already exists) -> run the Hito 6 pipeline as a subprocess ->
       mark ``completed``

Any exception after ``processing`` marks the row ``failed`` with the error
message, logs at ERROR, and exits 1. No row ever stays zombie in
``processing`` after the process ends.

The CSV at ``data/raw/telemetry_YYYY-MM-DD.csv`` is a backup/audit snapshot.
The pipeline reads from ``telemetry_events`` in the database (SQL/watermark),
never from this file.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import shlex
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Ensure the repo root is importable when run as `python scripts/nightly_export.py`.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import text  # noqa: E402

from services import job_runner  # noqa: E402

JOB_NAME = "nightly_export"

CSV_PREFIX = "telemetry_"
CSV_COLUMNS = (
    "id",
    "event_id",
    "timestamp",
    "event_type",
    "service",
    "user_id",
    "session_id",
    "tags",
)

_TARGET_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DEFAULT_PIPELINE_TIMEOUT_SECONDS = 1800
_LOG_TAIL_LINES = 20

logger = logging.getLogger("nightly_export")


def resolve_target_date() -> date:
    """Return ``TARGET_DATE`` (``YYYY-MM-DD``) or yesterday in UTC by default."""
    raw = os.getenv("TARGET_DATE")
    if raw is None or not raw.strip():
        return datetime.now(timezone.utc).date() - timedelta(days=1)
    value = raw.strip()
    if not _TARGET_DATE_RE.match(value):
        raise ValueError(f"TARGET_DATE must be YYYY-MM-DD, got {value!r}")
    return date.fromisoformat(value)


def _day_window(target: date) -> tuple[datetime, datetime]:
    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def export_telemetry_csv(engine, target: date, raw_dir: Path) -> dict[str, object]:
    """Export ``target`` day rows from ``telemetry_events`` to CSV (backup only).

    Skips writing when the file already exists (idempotent). Returns
    ``{"path": str, "rows": int | None, "skipped": bool}``.
    """
    path = raw_dir / f"{CSV_PREFIX}{target.isoformat()}.csv"
    if path.exists():
        logger.info(
            "job=%s target_date=%s status=export_skipped reason=csv_exists path=%s",
            JOB_NAME,
            target.isoformat(),
            path,
        )
        return {"path": str(path), "rows": None, "skipped": True}

    raw_dir.mkdir(parents=True, exist_ok=True)
    window_start, window_end = _day_window(target)
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    """
                    SELECT id, event_id, timestamp, event_type,
                           service, user_id, session_id, tags
                    FROM telemetry_events
                    WHERE timestamp >= :window_start
                      AND timestamp < :window_end
                    ORDER BY timestamp ASC
                    """
                ),
                {"window_start": window_start, "window_end": window_end},
            )
            .mappings()
            .all()
        )

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _cell(row[column]) for column in CSV_COLUMNS})

    logger.info(
        "job=%s target_date=%s status=exported rows=%s path=%s",
        JOB_NAME,
        target.isoformat(),
        len(rows),
        path,
    )
    return {"path": str(path), "rows": len(rows), "skipped": False}


def _default_pipeline_cmd() -> list[str]:
    override = os.getenv("PIPELINE_CMD")
    if override is not None and override.strip():
        return shlex.split(override.strip(), posix=(os.name != "nt"))
    # Hito 6 entry point: monthly pipeline CLI (idempotent upsert + run lock).
    return [sys.executable, "data/pipelines/pipeline.py"]


def run_pipeline_subprocess(
    cmd: list[str], *, cwd: Path, timeout_seconds: int
) -> None:
    """Run the Hito 6 pipeline out-of-process; raise on failure or timeout."""
    logger.info(
        "job=%s status=pipeline_start cmd=%s",
        JOB_NAME,
        " ".join(cmd),
    )
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"pipeline subprocess timed out after {timeout_seconds}s: "
            f"{' '.join(cmd)} ({exc})"
        ) from exc
    output = (completed.stdout or "") + (completed.stderr or "")
    tail = "\n".join(output.strip().splitlines()[-_LOG_TAIL_LINES:])
    if completed.returncode != 0:
        raise RuntimeError(
            f"pipeline subprocess failed (exit {completed.returncode}): "
            f"{' '.join(cmd)}\n{tail}"
        )
    if tail:
        logger.info("job=%s status=pipeline_output tail:\n%s", JOB_NAME, tail)
    logger.info("job=%s status=pipeline_ok exit=0", JOB_NAME)


def main(
    *,
    engine=None,
    raw_dir: Path | None = None,
    pipeline_cmd: list[str] | None = None,
    timeout_seconds: int | None = None,
) -> int:
    """Run one nightly cycle. Exit codes: 0 ok/skip, 1 failure, 2 bad date."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        target = resolve_target_date()
    except ValueError as exc:
        logger.error("job=%s status=failed reason=bad_target_date error=%s", JOB_NAME, exc)
        return 2

    if engine is None:
        try:
            from services.app.core.database import get_engine

            engine = get_engine()
        except RuntimeError as exc:
            logger.error(
                "job=%s target_date=%s status=failed reason=db_not_configured error=%s",
                JOB_NAME,
                target.isoformat(),
                exc,
            )
            return 1

    resolved_raw_dir = raw_dir or (_ROOT / "data" / "raw")
    resolved_cmd = pipeline_cmd or _default_pipeline_cmd()
    resolved_timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else int(os.getenv("PIPELINE_TIMEOUT_SECONDS", str(_DEFAULT_PIPELINE_TIMEOUT_SECONDS)))
    )

    try:
        job_runner.ensure_job_runs_schema(engine)
    except Exception as exc:  # noqa: BLE001 — nothing recorded yet, fail loudly
        logger.error(
            "job=%s target_date=%s status=failed reason=schema_error error=%s",
            JOB_NAME,
            target.isoformat(),
            exc,
        )
        return 1

    if job_runner.has_processing_lock(engine, job_name=JOB_NAME):
        logger.info(
            "job=%s target_date=%s status=lock_skipped "
            "reason=another_instance_processing",
            JOB_NAME,
            target.isoformat(),
        )
        return 0

    if job_runner.has_completed_for_date(engine, job_name=JOB_NAME, target_date=target):
        logger.info(
            "job=%s target_date=%s status=duplicate_skipped reason=already_completed",
            JOB_NAME,
            target.isoformat(),
        )
        return 0

    run_id = job_runner.create_job_run(engine, job_name=JOB_NAME, target_date=target)
    job_runner.mark_processing(engine, run_id=run_id)
    logger.info(
        "job=%s target_date=%s status=processing run_id=%s",
        JOB_NAME,
        target.isoformat(),
        run_id,
    )

    try:
        export_telemetry_csv(engine, target, resolved_raw_dir)
        run_pipeline_subprocess(resolved_cmd, cwd=_ROOT, timeout_seconds=resolved_timeout)
        job_runner.mark_completed(engine, run_id=run_id)
    except Exception as exc:  # noqa: BLE001 — every failure must land in `failed`
        try:
            job_runner.mark_failed(engine, run_id=run_id, error=str(exc))
        except Exception:  # noqa: BLE001
            logger.exception(
                "job=%s target_date=%s status=failed_persist_error run_id=%s",
                JOB_NAME,
                target.isoformat(),
                run_id,
            )
        logger.exception(
            "job=%s target_date=%s status=failed run_id=%s error=%s",
            JOB_NAME,
            target.isoformat(),
            run_id,
            exc,
        )
        return 1

    logger.info(
        "job=%s target_date=%s status=completed run_id=%s",
        JOB_NAME,
        target.isoformat(),
        run_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
