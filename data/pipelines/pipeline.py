"""HealthCore Monthly Clinic Supply Performance pipeline (Prefect).

Phase 1: extract → transform → load + optional eval snapshot.
Phase 2: retries on DB tasks, transform cache (1h), explicit optional failure handling.
Phase 3: idempotent upsert load + reporting.pipeline_runs execution log.
Phase 4: CLI + monthly cadence (documented in PIPELINE_DESIGN §6.3).
Phase 5: query/trigger helpers for services/reporting endpoints.

Part 3 refactor — the main flow is now a thin coordinator over reusable
subflows (``@flow``), each with explicit inputs/outputs and independently
runnable:

  * ``extract_supply_telemetry_flow``            (Extract)
  * ``transform_monthly_clinic_kpis_flow``       (Transform — one task per KPI)
  * ``load_monthly_clinic_supply_performance_flow`` (Load)
  * ``snapshot_monthly_clinic_kpis_flow``        (optional, ``return_state=True``)

The Transform subflow fans out to one task per CONTEXT KPI
(``transform_supply_cost_per_clinic``, ``transform_supply_consumption_volume``,
``transform_critical_stockout_frequency``, ``transform_expiry_risk_count``) and
composes the per-clinic rows. A per-``(pipeline_name, month_start)`` run lock
(§6.5) rejects overlapping runs of the same board month.

Run from the repo root (requires SUPABASE_DB_* or DATABASE_URL):

    PYTHONPATH=. uv run python data/pipelines/pipeline.py

When PREFECT_API_URL is set (local Prefect server or Cloud), the CLI invokes the
@flow engine. Otherwise it runs the same tasks via ``.fn()`` so the ETL works
even if the ephemeral Prefect API cannot start (common on Windows paths with
spaces).

Cadence (CONTEXT): monthly — ready by the first working day of the month (UTC).
Default month_start is the previous calendar month UTC.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from prefect import flow, task
from prefect.tasks import task_input_hash
from sqlalchemy import bindparam, text

# Ensure repo root is importable when run as a script.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from data.process.reporting.monthly_clinic_kpis import (  # noqa: E402
    SUPPLY_EVENT_TYPES,
    compose_monthly_clinic_kpi_rows,
    compute_critical_stockout_frequency,
    compute_expiry_risk_count,
    compute_supply_consumption_volume,
    compute_supply_cost_per_clinic,
)
from services.app.core.database import (  # noqa: E402
    get_engine,
    is_inventory_db_configured,
)

logger = logging.getLogger(__name__)

PIPELINE_NAME = "monthly_clinic_supply_performance"
SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "reporting_schema.sql"
EVAL_DIR = _REPO_ROOT / "data" / "eval"

# Transient Supabase / network blips usually clear within ~30s; 3 attempts × 10s
# covers typical pooler timeouts without stalling a monthly board run for minutes.
_DB_TASK_RETRIES = 3
_DB_RETRY_DELAY_SECONDS = 10

# Board pack is monthly; within one hour a re-run (manual retry / overlapping click)
# should reuse the same transform result for identical inputs.
_TRANSFORM_CACHE_EXPIRATION = timedelta(hours=1)

# Concurrency guard (PIPELINE_DESIGN §6.5): a `running` row younger than this is
# treated as a live run holding the month lock. Older `running` rows are assumed
# orphaned by a crashed process and no longer block a new attempt.
_RUN_LOCK_STALE_AFTER = timedelta(minutes=30)


class ConcurrentRunError(RuntimeError):
    """Raised when another live run already holds the lock for this board month."""


def _previous_month_start(today: date | None = None) -> date:
    """First day of the previous calendar month (UTC date)."""
    base = today or datetime.now(timezone.utc).date()
    first_this_month = base.replace(day=1)
    last_prev = first_this_month - timedelta(days=1)
    return last_prev.replace(day=1)


def _month_window(month_start: date) -> tuple[datetime, datetime]:
    start = datetime(month_start.year, month_start.month, 1, tzinfo=timezone.utc)
    if month_start.month == 12:
        end = datetime(month_start.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(month_start.year, month_start.month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _ensure_reporting_schema() -> None:
    sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(sql))


def _serialize_row(row: Any) -> dict[str, Any]:
    mapping = dict(row._mapping)
    ts = mapping.get("timestamp")
    if isinstance(ts, datetime):
        mapping["timestamp"] = ts.isoformat()
    tags = mapping.get("tags")
    if tags is None:
        mapping["tags"] = {}
    elif not isinstance(tags, dict):
        mapping["tags"] = dict(tags) if hasattr(tags, "keys") else {}
    return mapping


def _build_result(
    *,
    run_id: str,
    month_start: date,
    records_extracted: int,
    records_processed: int,
    eval_snapshot_ok: bool,
    status: str = "completed",
    error_message: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "run_id": run_id,
        "month_start": month_start.isoformat(),
        "records_extracted": records_extracted,
        "records_processed": records_processed,
        "eval_snapshot_ok": eval_snapshot_ok,
        "status": status,
    }
    if error_message:
        out["error_message"] = error_message
    return out


def _start_pipeline_run(run_id: UUID, month_start: date) -> datetime:
    """Insert a running row into reporting.pipeline_runs (audit log).

    Acts as the per-``(pipeline_name, month_start)`` run lock: the check for an
    existing live ``running`` row and the insert of this run's ``running`` row
    happen in one transaction, so two overlapping runs of the same board month
    cannot both proceed. A stale ``running`` row (older than
    ``_RUN_LOCK_STALE_AFTER``, assumed crashed) does not block a new attempt.
    """
    _ensure_reporting_schema()
    started_at = datetime.now(timezone.utc)
    window_start, window_end = _month_window(month_start)
    stale_cutoff = started_at - _RUN_LOCK_STALE_AFTER
    with get_engine().begin() as conn:
        live = conn.execute(
            text(
                """
                SELECT run_id, started_at
                FROM reporting.pipeline_runs
                WHERE pipeline_name = :pipeline_name
                  AND month_start = :month_start
                  AND status = 'running'
                  AND started_at >= :stale_cutoff
                ORDER BY started_at DESC
                LIMIT 1
                FOR UPDATE
                """
            ),
            {
                "pipeline_name": PIPELINE_NAME,
                "month_start": month_start,
                "stale_cutoff": stale_cutoff,
            },
        ).mappings().first()
        if live is not None:
            raise ConcurrentRunError(
                f"A run for {PIPELINE_NAME} month_start={month_start.isoformat()} "
                f"is already in progress (run_id={live['run_id']}, "
                f"started_at={live['started_at']})."
            )
        conn.execute(
            text(
                """
                INSERT INTO reporting.pipeline_runs (
                    run_id,
                    pipeline_name,
                    month_start,
                    started_at,
                    status,
                    phase,
                    records_processed,
                    window_start,
                    window_end
                ) VALUES (
                    :run_id,
                    :pipeline_name,
                    :month_start,
                    :started_at,
                    'running',
                    'extract',
                    0,
                    :window_start,
                    :window_end
                )
                """
            ),
            {
                "run_id": str(run_id),
                "pipeline_name": PIPELINE_NAME,
                "month_start": month_start,
                "started_at": started_at,
                "window_start": window_start,
                "window_end": window_end,
            },
        )
    return started_at


def _finish_pipeline_run(
    run_id: UUID,
    *,
    status: str,
    phase: str,
    records_extracted: int | None = None,
    records_processed: int = 0,
    error_message: str | None = None,
) -> None:
    """Finalize pipeline_runs with finished_at, status, counts, and optional error."""
    finished_at = datetime.now(timezone.utc)
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE reporting.pipeline_runs
                SET
                    finished_at = :finished_at,
                    status = :status,
                    phase = :phase,
                    records_extracted = COALESCE(:records_extracted, records_extracted),
                    records_processed = :records_processed,
                    error_message = :error_message,
                    computed_at = now()
                WHERE run_id = :run_id
                """
            ),
            {
                "run_id": str(run_id),
                "finished_at": finished_at,
                "status": status,
                "phase": phase,
                "records_extracted": records_extracted,
                "records_processed": records_processed,
                "error_message": error_message,
            },
        )


def _set_pipeline_phase(run_id: UUID, phase: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                UPDATE reporting.pipeline_runs
                SET phase = :phase, computed_at = now()
                WHERE run_id = :run_id
                """
            ),
            {"run_id": str(run_id), "phase": phase},
        )


def get_latest_pipeline_run(
    pipeline_name: str = PIPELINE_NAME,
) -> dict[str, Any] | None:
    """Return the most recent pipeline_runs row (for reporting endpoints)."""
    if not is_inventory_db_configured():
        return None
    _ensure_reporting_schema()
    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    run_id,
                    pipeline_name,
                    month_start,
                    started_at,
                    finished_at,
                    status,
                    phase,
                    records_processed,
                    records_extracted,
                    window_start,
                    window_end,
                    error_message
                FROM reporting.pipeline_runs
                WHERE pipeline_name = :pipeline_name
                ORDER BY started_at DESC
                LIMIT 1
                """
            ),
            {"pipeline_name": pipeline_name},
        ).mappings().first()
    if row is None:
        return None
    data = dict(row)
    for key in ("started_at", "finished_at", "window_start", "window_end", "month_start"):
        value = data.get(key)
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
    if data.get("run_id") is not None:
        data["run_id"] = str(data["run_id"])
    return data


def query_monthly_clinic_supply_performance(
    month_start: date | None = None,
) -> dict[str, Any]:
    """Read KPI rows for one month (defaults to the latest computed month)."""
    if not is_inventory_db_configured():
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL or SUPABASE_DB_* in .env"
        )
    _ensure_reporting_schema()
    engine = get_engine()
    with engine.connect() as conn:
        resolved = month_start
        if resolved is None:
            latest = conn.execute(
                text(
                    """
                    SELECT MAX(month_start) AS month_start
                    FROM reporting.monthly_clinic_supply_performance
                    """
                )
            ).mappings().first()
            if latest is None or latest["month_start"] is None:
                return {"month_start": None, "clinics": []}
            resolved = latest["month_start"]
            if isinstance(resolved, datetime):
                resolved = resolved.date()

        rows = conn.execute(
            text(
                """
                SELECT
                    clinic_id,
                    country,
                    total_supply_cost,
                    supply_consumption_count,
                    critical_stockout_count,
                    expiry_risk_count,
                    currency
                FROM reporting.monthly_clinic_supply_performance
                WHERE month_start = :month_start
                ORDER BY clinic_id ASC
                """
            ),
            {"month_start": resolved},
        ).mappings().all()

    clinics: list[dict[str, Any]] = []
    for row in rows:
        clinics.append(
            {
                "clinic_id": str(row["clinic_id"]),
                "country": row["country"],
                "total_supply_cost": float(row["total_supply_cost"] or 0),
                "supply_consumption_count": int(row["supply_consumption_count"] or 0),
                "critical_stockout_count": int(row["critical_stockout_count"] or 0),
                "expiry_risk_count": int(row["expiry_risk_count"] or 0),
                "currency": row["currency"],
            }
        )

    month_iso = (
        resolved.isoformat() if hasattr(resolved, "isoformat") else str(resolved)
    )
    return {"month_start": month_iso, "clinics": clinics}


def trigger_monthly_clinic_supply_performance_run(
    month_start: date | None = None,
) -> dict[str, Any]:
    """Manual trigger entry-point for POST /reporting/pipeline-runs (no ETL in services)."""
    return run_monthly_clinic_supply_performance(month_start=month_start)


@task(
    name="extract_supply_telemetry",
    # Retries=3: absorbs transient Supabase pooler disconnects / TLS blips on read.
    retries=_DB_TASK_RETRIES,
    retry_delay_seconds=_DB_RETRY_DELAY_SECONDS,
)
def extract_supply_telemetry(month_start: date) -> list[dict[str, Any]]:
    """Read-only extract of mandatory supply events for one calendar month."""
    if not is_inventory_db_configured():
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL or SUPABASE_DB_* in .env"
        )

    window_start, window_end = _month_window(month_start)
    event_types = sorted(SUPPLY_EVENT_TYPES)
    sql = text(
        """
        SELECT event_id, timestamp, event_type, tags
        FROM telemetry_events
        WHERE event_type IN :event_types
          AND timestamp >= :window_start
          AND timestamp < :window_end
        ORDER BY timestamp ASC
        """
    ).bindparams(bindparam("event_types", expanding=True))

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            sql,
            {
                "event_types": event_types,
                "window_start": window_start,
                "window_end": window_end,
            },
        )
        rows = [_serialize_row(row) for row in result]

    logger.info(
        "extract_supply_telemetry month_start=%s events=%s window=[%s, %s)",
        month_start.isoformat(),
        len(rows),
        window_start.isoformat(),
        window_end.isoformat(),
    )
    return rows


@task(
    name="transform_supply_cost_per_clinic",
    # Cache key = hash of task inputs (events + month_start). A near-term re-run
    # of the same month with identical events reuses the KPI result.
    cache_key_fn=task_input_hash,
    cache_expiration=_TRANSFORM_CACHE_EXPIRATION,
)
def transform_supply_cost_per_clinic(
    events: list[dict[str, Any]],
    month_start: date,
) -> dict[tuple[str, str], float]:
    """KPI — Supply Cost per Clinic: sum(unit_cost * quantity) of inbound orders."""
    result = compute_supply_cost_per_clinic(events, month_start)
    logger.info(
        "transform_supply_cost_per_clinic month_start=%s clinics=%s",
        month_start.isoformat(),
        len(result),
    )
    return result


@task(
    name="transform_supply_consumption_volume",
    cache_key_fn=task_input_hash,
    cache_expiration=_TRANSFORM_CACHE_EXPIRATION,
)
def transform_supply_consumption_volume(
    events: list[dict[str, Any]],
    month_start: date,
) -> dict[tuple[str, str], int]:
    """KPI — Supply Consumption Volume: count of outbound_order_created events."""
    result = compute_supply_consumption_volume(events, month_start)
    logger.info(
        "transform_supply_consumption_volume month_start=%s clinics=%s",
        month_start.isoformat(),
        len(result),
    )
    return result


@task(
    name="transform_critical_stockout_frequency",
    cache_key_fn=task_input_hash,
    cache_expiration=_TRANSFORM_CACHE_EXPIRATION,
)
def transform_critical_stockout_frequency(
    events: list[dict[str, Any]],
    month_start: date,
) -> dict[tuple[str, str], int]:
    """KPI — Critical Stockout Frequency: count of stock_threshold_triggered events."""
    result = compute_critical_stockout_frequency(events, month_start)
    logger.info(
        "transform_critical_stockout_frequency month_start=%s clinics=%s",
        month_start.isoformat(),
        len(result),
    )
    return result


@task(
    name="transform_expiry_risk_count",
    cache_key_fn=task_input_hash,
    cache_expiration=_TRANSFORM_CACHE_EXPIRATION,
)
def transform_expiry_risk_count(
    events: list[dict[str, Any]],
    month_start: date,
) -> dict[tuple[str, str], int]:
    """KPI — Expiry Risk Count: count of supply_expiry_flagged events."""
    result = compute_expiry_risk_count(events, month_start)
    logger.info(
        "transform_expiry_risk_count month_start=%s clinics=%s",
        month_start.isoformat(),
        len(result),
    )
    return result


@task(
    name="load_monthly_clinic_supply_performance",
    # Retries=3: write path is most exposed to statement timeouts; short backoff retries.
    retries=_DB_TASK_RETRIES,
    retry_delay_seconds=_DB_RETRY_DELAY_SECONDS,
)
def load_monthly_clinic_supply_performance(
    rows: list[dict[str, Any]],
    month_start: date,
) -> dict[str, Any]:
    """Idempotent upsert into reporting.monthly_clinic_supply_performance.

    Natural key UNIQUE (clinic_id, month_start): a second run with the same
    aggregates overwrites the same rows — no duplicates, same KPI result.
    """
    if not is_inventory_db_configured():
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL or SUPABASE_DB_* in .env"
        )

    _ensure_reporting_schema()
    engine = get_engine()
    upsert = text(
        """
        INSERT INTO reporting.monthly_clinic_supply_performance (
            clinic_id,
            country,
            month_start,
            total_supply_cost,
            supply_consumption_count,
            critical_stockout_count,
            expiry_risk_count,
            currency,
            computed_at
        ) VALUES (
            :clinic_id,
            :country,
            :month_start,
            :total_supply_cost,
            :supply_consumption_count,
            :critical_stockout_count,
            :expiry_risk_count,
            :currency,
            now()
        )
        ON CONFLICT (clinic_id, month_start) DO UPDATE SET
            country = EXCLUDED.country,
            total_supply_cost = EXCLUDED.total_supply_cost,
            supply_consumption_count = EXCLUDED.supply_consumption_count,
            critical_stockout_count = EXCLUDED.critical_stockout_count,
            expiry_risk_count = EXCLUDED.expiry_risk_count,
            currency = EXCLUDED.currency,
            computed_at = now()
        """
    )

    payload = [
        {
            "clinic_id": row["clinic_id"],
            "country": row["country"],
            "month_start": month_start,
            "total_supply_cost": row["total_supply_cost"],
            "supply_consumption_count": row["supply_consumption_count"],
            "critical_stockout_count": row["critical_stockout_count"],
            "expiry_risk_count": row["expiry_risk_count"],
            "currency": row["currency"],
        }
        for row in rows
    ]

    with engine.begin() as conn:
        if payload:
            conn.execute(upsert, payload)

    result = {
        "records_processed": len(payload),
        "month_start": month_start.isoformat(),
        "pipeline_name": PIPELINE_NAME,
    }
    logger.info(
        "load_monthly_clinic_supply_performance month_start=%s records=%s",
        month_start.isoformat(),
        len(payload),
    )
    return result


@task(name="write_eval_snapshot")
def write_eval_snapshot(
    rows: list[dict[str, Any]],
    month_start: date,
) -> str:
    """Optional non-critical step: persist KPI rows under data/eval/ for validation."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = (
        EVAL_DIR / f"monthly_clinic_supply_performance_{month_start.isoformat()}.json"
    )
    payload = {
        "month_start": month_start.isoformat(),
        "pipeline_name": PIPELINE_NAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clinics": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("write_eval_snapshot path=%s clinics=%s", out_path, len(rows))
    return str(out_path)


def run_monthly_clinic_supply_performance(
    month_start: date | None = None,
) -> dict[str, Any]:
    """Run ETL by calling task/transform functions directly (no Prefect API).

    Windows-safe fallback used by the CLI when ``PREFECT_API_URL`` is unset
    (the ephemeral Prefect API cannot start on paths with spaces). It reuses the
    same pure transform composition as the Transform subflow, so both paths
    produce identical rows.
    """
    resolved_month = month_start or _previous_month_start()
    run_uuid = uuid4()
    run_id = str(run_uuid)
    records_extracted = 0
    records_processed = 0
    logger.info(
        "run_monthly_clinic_supply_performance start run_id=%s month_start=%s",
        run_id,
        resolved_month.isoformat(),
    )

    try:
        _start_pipeline_run(run_uuid, resolved_month)

        events = extract_supply_telemetry.fn(resolved_month)
        records_extracted = len(events)
        _set_pipeline_phase(run_uuid, "transform")

        kpi_rows = compose_monthly_clinic_kpi_rows(
            month_start=resolved_month,
            supply_cost=transform_supply_cost_per_clinic.fn(events, resolved_month),
            consumption_volume=transform_supply_consumption_volume.fn(
                events, resolved_month
            ),
            stockout_frequency=transform_critical_stockout_frequency.fn(
                events, resolved_month
            ),
            expiry_risk=transform_expiry_risk_count.fn(events, resolved_month),
        )
        _set_pipeline_phase(run_uuid, "load")

        load_result = load_monthly_clinic_supply_performance.fn(
            kpi_rows, resolved_month
        )
        records_processed = load_result["records_processed"]

        eval_snapshot_ok = True
        try:
            write_eval_snapshot.fn(kpi_rows, resolved_month)
        except Exception as exc:  # noqa: BLE001 — optional step must not fail the ETL
            eval_snapshot_ok = False
            logger.warning(
                "write_eval_snapshot failed (non-critical); KPI load already committed: %s",
                exc,
            )

        _finish_pipeline_run(
            run_uuid,
            status="completed",
            phase="load",
            records_extracted=records_extracted,
            records_processed=records_processed,
        )
        return _build_result(
            run_id=run_id,
            month_start=resolved_month,
            records_extracted=records_extracted,
            records_processed=records_processed,
            eval_snapshot_ok=eval_snapshot_ok,
        )
    except Exception as exc:
        logger.exception("pipeline failed run_id=%s", run_id)
        try:
            _finish_pipeline_run(
                run_uuid,
                status="failed",
                phase="failed",
                records_extracted=records_extracted,
                records_processed=records_processed,
                error_message=str(exc)[:2000],
            )
        except Exception:  # noqa: BLE001
            logger.exception("could not persist failed pipeline_runs row")
        raise


# --------------------------------------------------------------------------- #
# Subflows — each phase is an independent @flow with explicit inputs/outputs.
# The main flow (below) coordinates them but contains none of their logic.
# --------------------------------------------------------------------------- #


@flow(name="extract_supply_telemetry_flow")
def extract_supply_telemetry_flow(month_start: date) -> list[dict[str, Any]]:
    """Extract subflow — read mandatory supply events for one calendar month.

    Input: ``month_start``. Output: raw serializable telemetry event dicts.
    Runnable on its own to inspect what the extract window returns.
    """
    return extract_supply_telemetry(month_start)


@flow(name="transform_monthly_clinic_kpis_flow")
def transform_monthly_clinic_kpis_flow(
    events: list[dict[str, Any]],
    month_start: date,
) -> list[dict[str, Any]]:
    """Transform subflow — fan out to one task per CONTEXT KPI, then compose rows.

    Input: extracted ``events`` + ``month_start``. Output: per-clinic KPI rows
    ready for upsert. Each KPI task is independently cached and testable.
    """
    supply_cost = transform_supply_cost_per_clinic(events, month_start)
    consumption_volume = transform_supply_consumption_volume(events, month_start)
    stockout_frequency = transform_critical_stockout_frequency(events, month_start)
    expiry_risk = transform_expiry_risk_count(events, month_start)

    rows = compose_monthly_clinic_kpi_rows(
        month_start=month_start,
        supply_cost=supply_cost,
        consumption_volume=consumption_volume,
        stockout_frequency=stockout_frequency,
        expiry_risk=expiry_risk,
    )
    logger.info(
        "transform_monthly_clinic_kpis_flow month_start=%s clinics=%s",
        month_start.isoformat(),
        len(rows),
    )
    return rows


@flow(name="load_monthly_clinic_supply_performance_flow")
def load_monthly_clinic_supply_performance_flow(
    rows: list[dict[str, Any]],
    month_start: date,
) -> dict[str, Any]:
    """Load subflow — idempotent upsert of KPI rows into the reporting table.

    Input: composed KPI ``rows`` + ``month_start``. Output: load result dict
    (records_processed, month_start, pipeline_name). Fails the run if the
    critical load task does not complete.
    """
    load_state = load_monthly_clinic_supply_performance(
        rows, month_start, return_state=True
    )
    if load_state is None or not load_state.is_completed():
        raise RuntimeError(
            f"load_monthly_clinic_supply_performance failed: {load_state}"
        )
    return load_state.result()


@flow(name="snapshot_monthly_clinic_kpis_flow")
def snapshot_monthly_clinic_kpis_flow(
    rows: list[dict[str, Any]],
    month_start: date,
) -> str:
    """Optional subflow — persist a KPI snapshot under data/eval/ for validation.

    Non-critical: the main flow invokes it with ``return_state=True`` so a
    failure here never fails a run whose KPI load already committed.
    """
    return write_eval_snapshot(rows, month_start)


@flow(name="monthly_clinic_supply_performance_flow")
def monthly_clinic_supply_performance_flow(
    month_start: date | None = None,
) -> dict[str, Any]:
    """Main ETL flow — thin coordinator over the extract/transform/load subflows.

    Owns run-lifecycle audit (pipeline_runs) and phase transitions; delegates all
    ETL logic to the subflows. The optional snapshot subflow is invoked with
    ``return_state=True`` so it cannot fail a committed run.
    """
    resolved_month = month_start or _previous_month_start()
    run_uuid = uuid4()
    run_id = str(run_uuid)
    records_extracted = 0
    records_processed = 0
    logger.info(
        "monthly_clinic_supply_performance_flow start run_id=%s month_start=%s",
        run_id,
        resolved_month.isoformat(),
    )

    try:
        _start_pipeline_run(run_uuid, resolved_month)

        events = extract_supply_telemetry_flow(resolved_month)
        records_extracted = len(events)
        _set_pipeline_phase(run_uuid, "transform")

        kpi_rows = transform_monthly_clinic_kpis_flow(events, resolved_month)
        _set_pipeline_phase(run_uuid, "load")

        load_result = load_monthly_clinic_supply_performance_flow(
            kpi_rows, resolved_month
        )
        records_processed = load_result["records_processed"]

        snapshot_state = snapshot_monthly_clinic_kpis_flow(
            kpi_rows, resolved_month, return_state=True
        )
        snapshot_ok = snapshot_state is not None and snapshot_state.is_completed()
        if not snapshot_ok:
            logger.warning(
                "snapshot_monthly_clinic_kpis_flow failed (non-critical); "
                "KPI load already committed. state=%s",
                snapshot_state,
            )

        _finish_pipeline_run(
            run_uuid,
            status="completed",
            phase="load",
            records_extracted=records_extracted,
            records_processed=records_processed,
        )
        return _build_result(
            run_id=run_id,
            month_start=resolved_month,
            records_extracted=records_extracted,
            records_processed=records_processed,
            eval_snapshot_ok=snapshot_ok,
        )
    except Exception as exc:
        logger.exception("pipeline flow failed run_id=%s", run_id)
        try:
            _finish_pipeline_run(
                run_uuid,
                status="failed",
                phase="failed",
                records_extracted=records_extracted,
                records_processed=records_processed,
                error_message=str(exc)[:2000],
            )
        except Exception:  # noqa: BLE001
            logger.exception("could not persist failed pipeline_runs row")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    # CLI: PYTHONPATH=. uv run python data/pipelines/pipeline.py
    if os.getenv("PREFECT_API_URL"):
        result = monthly_clinic_supply_performance_flow()
    else:
        logger.info(
            "PREFECT_API_URL unset — running via task.fn() "
            "(set PREFECT_API_URL to use the Prefect flow engine)"
        )
        result = run_monthly_clinic_supply_performance()
    print(json.dumps(result, indent=2))
