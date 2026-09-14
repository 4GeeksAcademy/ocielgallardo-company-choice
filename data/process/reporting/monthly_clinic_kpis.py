"""Pure aggregation for Monthly Clinic Supply Performance KPIs.

Each mandatory telemetry event maps to exactly one CONTEXT KPI (see
`docs/data-pipelines/CONTEXT-healthcore-phase-2.md` §2). This module keeps that
mapping as small, independently testable, pure functions so the Prefect
transform tasks in `data/pipelines/pipeline.py` can wrap them one-per-KPI:

- ``compute_supply_cost_per_clinic``        ← inbound_order_created  (sum unit_cost * quantity)
- ``compute_supply_consumption_volume``     ← outbound_order_created (count)
- ``compute_critical_stockout_frequency``   ← stock_threshold_triggered (count)
- ``compute_expiry_risk_count``             ← supply_expiry_flagged (count)

``normalize_supply_events`` performs the shared preparation (dedupe by
``event_id``, resolve ``clinic_id`` / ``country``, keep the target month).
``compose_monthly_clinic_kpi_rows`` merges the four KPI maps into the row shape
expected by ``reporting.monthly_clinic_supply_performance``. All functions take
in-memory telemetry-shaped dicts and never touch a database.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

SUPPLY_EVENT_TYPES = frozenset(
    {
        "inbound_order_created",
        "outbound_order_created",
        "stock_threshold_triggered",
        "supply_expiry_flagged",
    }
)

# (clinic_id, country) — the natural key each KPI is grouped by before the
# per-clinic rows are composed for upsert.
ClinicKey = tuple[str, str]


def _tags_as_dict(tags: Any) -> dict[str, Any]:
    if isinstance(tags, dict):
        return tags
    return {}


def _clinic_id_text(raw: Any) -> str | None:
    if raw is None:
        return None
    try:
        clinic = int(raw)
    except (TypeError, ValueError):
        text = str(raw).strip()
        if not text:
            return None
        try:
            clinic = int(text)
        except ValueError:
            return None
    if clinic < 1 or clinic > 12:
        return None
    return str(clinic)


def _country(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip().upper()
    if value in {"US", "UK"}:
        return value
    return None


def _currency_for_country(country: str) -> str:
    return "GBP" if country == "UK" else "USD"


def _as_float(raw: Any, default: float = 0.0) -> float:
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def normalize_supply_events(
    events: list[dict[str, Any]],
    month_start: date,
) -> pd.DataFrame:
    """Return a clean, deduped frame of in-month supply events.

    Shared preparation used by every per-KPI compute function:

    1. Keep only the four mandatory supply event types.
    2. Dedupe by ``event_id`` (keep earliest by ``timestamp``).
    3. Resolve ``clinic_id`` (integer text ``1``-``12``) and ``country``
       (``US``/``UK``); drop rows that fail either check.
    4. Keep only events whose UTC ``timestamp`` falls in the target month.
    5. Derive ``unit_cost``, ``quantity`` and ``line_cost`` for cost KPIs.

    The result is defensive by construction: malformed rows (null clinic id,
    non-numeric cost, missing tags, wrong event type) are dropped or coerced to
    ``0`` rather than raising.
    """
    empty = pd.DataFrame(
        columns=[
            "event_id",
            "timestamp",
            "event_type",
            "clinic_id",
            "country",
            "unit_cost",
            "quantity",
            "line_cost",
        ]
    )
    if not events:
        return empty

    frame = pd.DataFrame(events)
    if frame.empty:
        return empty

    for col in ("event_id", "timestamp", "event_type", "tags"):
        if col not in frame.columns:
            frame[col] = None

    frame = frame[frame["event_type"].isin(SUPPLY_EVENT_TYPES)].copy()
    if frame.empty:
        return empty

    # format="ISO8601": mixed offsets with/without fractional seconds. Pandas
    # otherwise infers from the first rows (seed events have no microseconds)
    # and coerces later live events to NaT, dropping them from the board pack.
    frame["timestamp"] = pd.to_datetime(
        frame["timestamp"], utc=True, errors="coerce", format="ISO8601"
    )
    frame = frame.dropna(subset=["timestamp", "event_id"])
    frame = frame.sort_values("timestamp", kind="mergesort")
    frame = frame.drop_duplicates(subset=["event_id"], keep="first")

    tags = frame["tags"].map(_tags_as_dict)
    frame["clinic_id"] = tags.map(lambda t: _clinic_id_text(t.get("clinic_id")))
    frame["country"] = tags.map(lambda t: _country(t.get("country")))
    frame["unit_cost"] = tags.map(lambda t: _as_float(t.get("unit_cost"), 0.0))
    frame["quantity"] = tags.map(lambda t: _as_float(t.get("quantity"), 0.0))
    frame["line_cost"] = frame["unit_cost"] * frame["quantity"]

    frame = frame.dropna(subset=["clinic_id", "country"])
    if frame.empty:
        return empty

    month_mask = (
        (frame["timestamp"].dt.year == month_start.year)
        & (frame["timestamp"].dt.month == month_start.month)
    )
    frame = frame.loc[month_mask]
    if frame.empty:
        return empty

    return frame.reset_index(drop=True)


def _ensure_frame(
    events_or_frame: list[dict[str, Any]] | pd.DataFrame,
    month_start: date,
) -> pd.DataFrame:
    """Accept either raw telemetry events or an already-normalized frame.

    This lets each KPI task be called in isolation with in-memory events
    (unit tests) while the transform subflow can normalize once and reuse it.
    """
    if isinstance(events_or_frame, pd.DataFrame):
        return events_or_frame
    return normalize_supply_events(events_or_frame, month_start)


def _clinic_keys(frame: pd.DataFrame) -> list[ClinicKey]:
    if frame.empty:
        return []
    pairs = frame[["clinic_id", "country"]].drop_duplicates()
    return [
        (str(row.clinic_id), str(row.country))
        for row in pairs.itertuples(index=False)
    ]


def compute_supply_cost_per_clinic(
    events_or_frame: list[dict[str, Any]] | pd.DataFrame,
    month_start: date,
) -> dict[ClinicKey, float]:
    """Supply Cost per Clinic: sum(unit_cost * quantity) of inbound orders.

    Returns ``{(clinic_id, country): total_supply_cost}`` for the month.
    """
    frame = _ensure_frame(events_or_frame, month_start)
    if frame.empty:
        return {}
    inbound = frame.loc[frame["event_type"] == "inbound_order_created"]
    if inbound.empty:
        return {}
    grouped = inbound.groupby(["clinic_id", "country"], sort=True)["line_cost"].sum()
    return {
        (str(clinic), str(country)): float(value)
        for (clinic, country), value in grouped.items()
    }


def _count_by_clinic(
    frame: pd.DataFrame,
    event_type: str,
) -> dict[ClinicKey, int]:
    subset = frame.loc[frame["event_type"] == event_type]
    if subset.empty:
        return {}
    grouped = subset.groupby(["clinic_id", "country"], sort=True).size()
    return {
        (str(clinic), str(country)): int(value)
        for (clinic, country), value in grouped.items()
    }


def compute_supply_consumption_volume(
    events_or_frame: list[dict[str, Any]] | pd.DataFrame,
    month_start: date,
) -> dict[ClinicKey, int]:
    """Supply Consumption Volume: count of outbound_order_created for the month."""
    frame = _ensure_frame(events_or_frame, month_start)
    if frame.empty:
        return {}
    return _count_by_clinic(frame, "outbound_order_created")


def compute_critical_stockout_frequency(
    events_or_frame: list[dict[str, Any]] | pd.DataFrame,
    month_start: date,
) -> dict[ClinicKey, int]:
    """Critical Stockout Frequency: count of stock_threshold_triggered events."""
    frame = _ensure_frame(events_or_frame, month_start)
    if frame.empty:
        return {}
    return _count_by_clinic(frame, "stock_threshold_triggered")


def compute_expiry_risk_count(
    events_or_frame: list[dict[str, Any]] | pd.DataFrame,
    month_start: date,
) -> dict[ClinicKey, int]:
    """Expiry Risk Count: count of supply_expiry_flagged events for the month."""
    frame = _ensure_frame(events_or_frame, month_start)
    if frame.empty:
        return {}
    return _count_by_clinic(frame, "supply_expiry_flagged")


def compose_monthly_clinic_kpi_rows(
    *,
    month_start: date,
    supply_cost: dict[ClinicKey, float],
    consumption_volume: dict[ClinicKey, int],
    stockout_frequency: dict[ClinicKey, int],
    expiry_risk: dict[ClinicKey, int],
) -> list[dict[str, Any]]:
    """Merge the four per-KPI maps into one row per (clinic_id, country).

    Every clinic key that appears in any KPI map yields exactly one row; KPIs
    with no events for that clinic default to ``0``. Currency is derived from
    country and never mixes ``USD``/``GBP`` within a row.
    """
    keys: set[ClinicKey] = set()
    for kpi_map in (supply_cost, consumption_volume, stockout_frequency, expiry_risk):
        keys.update(kpi_map.keys())

    rows: list[dict[str, Any]] = []
    for clinic_id, country in sorted(keys):
        key = (clinic_id, country)
        rows.append(
            {
                "clinic_id": clinic_id,
                "country": country,
                "month_start": month_start.isoformat(),
                "total_supply_cost": float(supply_cost.get(key, 0.0)),
                "supply_consumption_count": int(consumption_volume.get(key, 0)),
                "critical_stockout_count": int(stockout_frequency.get(key, 0)),
                "expiry_risk_count": int(expiry_risk.get(key, 0)),
                "currency": _currency_for_country(country),
            }
        )
    return rows


def aggregate_monthly_clinic_kpis(
    events: list[dict[str, Any]],
    month_start: date,
) -> list[dict[str, Any]]:
    """Dedupe by event_id and aggregate all four KPIs per clinic for one month.

    Composed from the per-KPI helpers so the CLI fallback path and the Prefect
    transform subflow produce identical rows. Returns serializable row dicts
    ready for upsert into reporting.monthly_clinic_supply_performance.
    """
    frame = normalize_supply_events(events, month_start)
    if frame.empty:
        return []

    return compose_monthly_clinic_kpi_rows(
        month_start=month_start,
        supply_cost=compute_supply_cost_per_clinic(frame, month_start),
        consumption_volume=compute_supply_consumption_volume(frame, month_start),
        stockout_frequency=compute_critical_stockout_frequency(frame, month_start),
        expiry_risk=compute_expiry_risk_count(frame, month_start),
    )
