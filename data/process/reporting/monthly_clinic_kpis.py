"""Pure aggregation for Monthly Clinic Supply Performance KPIs.

Maps mandatory telemetry events to CONTEXT fields:
- total_supply_cost ← inbound_order_created (sum unit_cost * quantity)
- supply_consumption_count ← outbound_order_created
- critical_stockout_count ← stock_threshold_triggered
- expiry_risk_count ← supply_expiry_flagged
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


def aggregate_monthly_clinic_kpis(
    events: list[dict[str, Any]],
    month_start: date,
) -> list[dict[str, Any]]:
    """Dedupe by event_id and aggregate KPIs per clinic for one month.

    Returns serializable row dicts ready for upsert into
    reporting.monthly_clinic_supply_performance.
    """
    if not events:
        return []

    frame = pd.DataFrame(events)
    if frame.empty:
        return []

    for col in ("event_id", "timestamp", "event_type", "tags"):
        if col not in frame.columns:
            frame[col] = None

    frame = frame[frame["event_type"].isin(SUPPLY_EVENT_TYPES)].copy()
    if frame.empty:
        return []

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
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
        return []

    # Keep only events that fall in the target calendar month (UTC).
    month_mask = (
        (frame["timestamp"].dt.year == month_start.year)
        & (frame["timestamp"].dt.month == month_start.month)
    )
    frame = frame.loc[month_mask]
    if frame.empty:
        return []

    rows: list[dict[str, Any]] = []
    grouped = frame.groupby(["clinic_id", "country"], sort=True, dropna=False)
    for (clinic_id, country), group in grouped:
        country_str = str(country)
        rows.append(
            {
                "clinic_id": str(clinic_id),
                "country": country_str,
                "month_start": month_start.isoformat(),
                "total_supply_cost": float(
                    group.loc[
                        group["event_type"] == "inbound_order_created", "line_cost"
                    ].sum()
                ),
                "supply_consumption_count": int(
                    (group["event_type"] == "outbound_order_created").sum()
                ),
                "critical_stockout_count": int(
                    (group["event_type"] == "stock_threshold_triggered").sum()
                ),
                "expiry_risk_count": int(
                    (group["event_type"] == "supply_expiry_flagged").sum()
                ),
                "currency": _currency_for_country(country_str),
            }
        )
    return rows
