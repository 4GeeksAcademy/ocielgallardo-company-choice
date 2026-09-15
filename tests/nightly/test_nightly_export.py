"""Tests for the nightly telemetry export (Hito 22, DEV-53).

SQLite-backed: ``services.job_runner`` uses portable SQL (ids and timestamps
are supplied from Python), so the full state machine runs without Supabase.
Production DDL stays Postgres (``data/pipelines/job_runs_schema.sql``).

Timestamp note: the export window binds real datetimes; in these tests the
``telemetry_events`` stand-in stores zero-padded ``YYYY-MM-DD HH:MM:SS+00:00``
strings, so day-boundary comparisons behave identically to timestamptz.

Run:
    uv run python -m pytest tests/nightly/test_nightly_export.py
"""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

# Make the repo root importable when pytest is invoked from elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from scripts import nightly_export  # noqa: E402
from services import job_runner  # noqa: E402

JOB = nightly_export.JOB_NAME
TARGET = date(2026, 9, 14)

_TELEMETRY_DDL = """
CREATE TABLE telemetry_events (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  event_type TEXT NOT NULL,
  service TEXT NOT NULL DEFAULT 'backoffice',
  user_id TEXT NOT NULL,
  session_id TEXT,
  tags TEXT NOT NULL DEFAULT '{}'
)
"""


@pytest.fixture()
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path}/jobs.db")
    job_runner.ensure_job_runs_schema(eng)
    with eng.begin() as conn:
        conn.execute(text(_TELEMETRY_DDL))
    yield eng
    eng.dispose()


def _insert_event(engine, event_id, timestamp, event_type="inbound_order_created"):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO telemetry_events
                    (id, event_id, timestamp, event_type, service,
                     user_id, session_id, tags)
                VALUES
                    (:id, :event_id, :timestamp, :event_type, 'backoffice',
                     'user-1', 'sess-1', '{"clinic_id": "3"}')
                """
            ),
            {
                "id": f"id-{event_id}",
                "event_id": event_id,
                "timestamp": timestamp,
                "event_type": event_type,
            },
        )


def _statuses(engine):
    with engine.connect() as conn:
        return [
            row[0]
            for row in conn.execute(text("SELECT status FROM job_runs")).all()
        ]


def _pipeline_stub(counter: Path, *, fail: bool = False) -> list[str]:
    code = (
        f"open({str(counter)!r}, 'a').write('x'); "
        f"import sys; sys.exit({1 if fail else 0})"
    )
    return [sys.executable, "-c", code]


# --------------------------------------------------------------------------- #
# State machine unit tests.
# --------------------------------------------------------------------------- #


def test_lifecycle_pending_to_completed(engine):
    run_id = job_runner.create_job_run(engine, job_name=JOB, target_date=TARGET)
    assert job_runner.get_run(engine, run_id=run_id)["status"] == "pending"

    job_runner.mark_processing(engine, run_id=run_id)
    assert job_runner.has_processing_lock(engine, job_name=JOB) is True

    job_runner.mark_completed(engine, run_id=run_id)
    assert job_runner.get_run(engine, run_id=run_id)["status"] == "completed"
    assert job_runner.has_processing_lock(engine, job_name=JOB) is False
    assert (
        job_runner.has_completed_for_date(engine, job_name=JOB, target_date=TARGET)
        is True
    )


def test_failed_never_stays_processing(engine):
    run_id = job_runner.create_job_run(engine, job_name=JOB, target_date=TARGET)
    job_runner.mark_processing(engine, run_id=run_id)
    job_runner.mark_failed(engine, run_id=run_id, error="boom" * 2000)

    row = job_runner.get_run(engine, run_id=run_id)
    assert row["status"] == "failed"
    assert row["finished_at"] is not None
    assert len(row["error_message"]) <= 2000
    assert "processing" not in _statuses(engine)


def test_completed_gate_is_per_date(engine):
    other = date(2026, 9, 13)
    run_id = job_runner.create_job_run(engine, job_name=JOB, target_date=other)
    job_runner.mark_processing(engine, run_id=run_id)
    job_runner.mark_completed(engine, run_id=run_id)

    assert (
        job_runner.has_completed_for_date(engine, job_name=JOB, target_date=other)
        is True
    )
    assert (
        job_runner.has_completed_for_date(engine, job_name=JOB, target_date=TARGET)
        is False
    )


# --------------------------------------------------------------------------- #
# End-to-end main() tests (stubbed pipeline subprocess).
# --------------------------------------------------------------------------- #


def test_main_success_exports_csv_and_completes(engine, tmp_path, monkeypatch):
    _insert_event(engine, "e-1", "2026-09-14 10:00:00+00:00")
    _insert_event(engine, "e-2", "2026-09-14 23:59:59+00:00")
    _insert_event(engine, "e-out", "2026-09-15 08:00:00+00:00")
    counter = tmp_path / "pipeline.runs"
    monkeypatch.setenv("TARGET_DATE", "2026-09-14")

    rc = nightly_export.main(
        engine=engine,
        raw_dir=tmp_path / "raw",
        pipeline_cmd=_pipeline_stub(counter),
        timeout_seconds=60,
    )

    assert rc == 0
    csv_path = tmp_path / "raw" / "telemetry_2026-09-14.csv"
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["event_id"] for row in rows] == ["e-1", "e-2"]
    assert counter.read_text() == "x"
    assert _statuses(engine) == ["completed"]


def test_main_second_run_same_date_is_noop(engine, tmp_path, monkeypatch):
    _insert_event(engine, "e-1", "2026-09-14 10:00:00+00:00")
    counter = tmp_path / "pipeline.runs"
    raw_dir = tmp_path / "raw"
    monkeypatch.setenv("TARGET_DATE", "2026-09-14")
    kwargs = {
        "engine": engine,
        "raw_dir": raw_dir,
        "pipeline_cmd": _pipeline_stub(counter),
        "timeout_seconds": 60,
    }

    assert nightly_export.main(**kwargs) == 0
    csv_path = raw_dir / "telemetry_2026-09-14.csv"
    before = csv_path.stat().st_mtime_ns

    assert nightly_export.main(**kwargs) == 0  # duplicate run

    assert csv_path.stat().st_mtime_ns == before  # CSV untouched
    assert counter.read_text() == "x"  # pipeline ran exactly once
    assert _statuses(engine) == ["completed"]  # no extra rows


def test_main_aborts_when_lock_held(engine, tmp_path, monkeypatch):
    run_id = job_runner.create_job_run(engine, job_name=JOB, target_date=TARGET)
    job_runner.mark_processing(engine, run_id=run_id)
    counter = tmp_path / "pipeline.runs"
    monkeypatch.setenv("TARGET_DATE", "2026-09-14")

    rc = nightly_export.main(
        engine=engine,
        raw_dir=tmp_path / "raw",
        pipeline_cmd=_pipeline_stub(counter),
        timeout_seconds=60,
    )

    assert rc == 0  # silent abort
    assert not counter.exists()  # pipeline never launched
    assert not (tmp_path / "raw" / "telemetry_2026-09-14.csv").exists()
    assert _statuses(engine) == ["processing"]  # lock row untouched


def test_main_pipeline_failure_marks_failed(engine, tmp_path, monkeypatch):
    _insert_event(engine, "e-1", "2026-09-14 10:00:00+00:00")
    counter = tmp_path / "pipeline.runs"
    monkeypatch.setenv("TARGET_DATE", "2026-09-14")

    rc = nightly_export.main(
        engine=engine,
        raw_dir=tmp_path / "raw",
        pipeline_cmd=_pipeline_stub(counter, fail=True),
        timeout_seconds=60,
    )

    assert rc == 1
    assert _statuses(engine) == ["failed"]
    with engine.connect() as conn:
        error = conn.execute(
            text("SELECT error_message FROM job_runs")
        ).scalar_one()
    assert "exit 1" in error


def test_main_bad_target_date_returns_2(engine, tmp_path, monkeypatch):
    monkeypatch.setenv("TARGET_DATE", "not-a-date")
    rc = nightly_export.main(
        engine=engine,
        raw_dir=tmp_path / "raw",
        pipeline_cmd=_pipeline_stub(tmp_path / "pipeline.runs"),
        timeout_seconds=60,
    )
    assert rc == 2
    assert _statuses(engine) == []


def test_main_skips_export_when_csv_exists(engine, tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    sentinel = raw_dir / "telemetry_2026-09-14.csv"
    sentinel.write_text("id,event_id\n", encoding="utf-8")
    counter = tmp_path / "pipeline.runs"
    monkeypatch.setenv("TARGET_DATE", "2026-09-14")

    rc = nightly_export.main(
        engine=engine,
        raw_dir=raw_dir,
        pipeline_cmd=_pipeline_stub(counter),
        timeout_seconds=60,
    )

    assert rc == 0
    assert sentinel.read_text(encoding="utf-8") == "id,event_id\n"
    assert _statuses(engine) == ["completed"]


# --------------------------------------------------------------------------- #
# PIPELINE_CMD override splitting (portable quoting).
# --------------------------------------------------------------------------- #


def test_split_pipeline_cmd_posix(monkeypatch):
    monkeypatch.setattr(nightly_export.os, "name", "posix")
    assert nightly_export._split_pipeline_cmd(
        "python data/pipelines/pipeline.py --no-prefect"
    ) == ["python", "data/pipelines/pipeline.py", "--no-prefect"]


def test_split_pipeline_cmd_windows_strips_quotes_but_keeps_backslashes(
    monkeypatch,
):
    monkeypatch.setattr(nightly_export.os, "name", "nt")
    assert nightly_export._split_pipeline_cmd(
        'python -c "import sys; sys.exit(3)"'
    ) == ["python", "-c", "import sys; sys.exit(3)"]
    assert nightly_export._split_pipeline_cmd(
        '"C:\\tools\\python.exe" data/pipelines/pipeline.py'
    ) == ["C:\\tools\\python.exe", "data/pipelines/pipeline.py"]
