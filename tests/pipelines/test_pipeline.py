"""Unit tests for the Monthly Clinic Supply Performance transformation tasks.

These tests exercise the four per-KPI Prefect transform tasks in isolation via
``.fn(...)`` — no live database, no Prefect API, no external services. Fixtures
are in-memory dicts shaped exactly like ``telemetry_events`` rows (envelope
columns + allowlisted ``tags``) as defined in
``docs/data-pipelines/CONTEXT-healthcore-phase-2.md`` and ``PIPELINE_DESIGN.md``.

KPI ↔ event mapping under test (CONTEXT §2):
    Supply Cost per Clinic      ← inbound_order_created   (sum unit_cost * quantity)
    Supply Consumption Volume   ← outbound_order_created  (count)
    Critical Stockout Frequency ← stock_threshold_triggered (count)
    Expiry Risk Count           ← supply_expiry_flagged   (count)

Run:
    python -m pytest tests/pipelines/test_pipeline.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

# Make the repo root importable when pytest is invoked from elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from data.pipelines.pipeline import (  # noqa: E402
    transform_critical_stockout_frequency,
    transform_expiry_risk_count,
    transform_supply_consumption_volume,
    transform_supply_cost_per_clinic,
)
from data.process.reporting.monthly_clinic_kpis import (  # noqa: E402
    aggregate_monthly_clinic_kpis,
)

JULY = date(2026, 7, 1)


def _event(
    event_id: str,
    event_type: str,
    *,
    clinic_id: Any = "3",
    country: Any = "US",
    timestamp: str = "2026-07-10T09:00:00Z",
    **tags: Any,
) -> dict[str, Any]:
    """Build one telemetry-events-shaped row (envelope + allowlisted tags)."""
    payload = {"clinic_id": clinic_id, "country": country}
    payload.update(tags)
    return {
        "event_id": event_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "tags": payload,
    }


# --------------------------------------------------------------------------- #
# Known-value tests (hand-calculated against the CONTEXT KPI definitions).
# --------------------------------------------------------------------------- #


def test_supply_cost_per_clinic_matches_context_definition() -> None:
    """Supply Cost per Clinic = sum(unit_cost * quantity) of inbound orders.

    Hand calc for clinic 3 (US):
        (12.50 * 4) + (3.00 * 10) = 50.00 + 30.00 = 80.00
    Outbound / stockout events must not contribute to cost.
    """
    events = [
        _event("in-1", "inbound_order_created", unit_cost=12.50, quantity=4),
        _event("in-2", "inbound_order_created", unit_cost=3.00, quantity=10),
        _event("out-1", "outbound_order_created"),
        _event("stk-1", "stock_threshold_triggered"),
    ]

    result = transform_supply_cost_per_clinic.fn(events, JULY)

    assert result == {("3", "US"): 80.00}


def test_supply_consumption_volume_counts_outbound_only() -> None:
    """Supply Consumption Volume = count of outbound_order_created for the month."""
    events = [
        _event("out-1", "outbound_order_created"),
        _event("out-2", "outbound_order_created"),
        _event("out-3", "outbound_order_created"),
        _event("in-1", "inbound_order_created", unit_cost=1, quantity=1),
    ]

    result = transform_supply_consumption_volume.fn(events, JULY)

    assert result == {("3", "US"): 3}


def test_critical_stockout_frequency_counts_threshold_events() -> None:
    """Critical Stockout Frequency = count of stock_threshold_triggered events."""
    events = [
        _event("stk-1", "stock_threshold_triggered"),
        _event("stk-2", "stock_threshold_triggered"),
        _event("out-1", "outbound_order_created"),
    ]

    result = transform_critical_stockout_frequency.fn(events, JULY)

    assert result == {("3", "US"): 2}


def test_expiry_risk_count_counts_expiry_flags() -> None:
    """Expiry Risk Count = count of supply_expiry_flagged events for the month."""
    events = [
        _event("exp-1", "supply_expiry_flagged"),
        _event("exp-2", "supply_expiry_flagged"),
        _event("exp-3", "supply_expiry_flagged"),
        _event("exp-4", "supply_expiry_flagged"),
    ]

    result = transform_expiry_risk_count.fn(events, JULY)

    assert result == {("3", "US"): 4}


# --------------------------------------------------------------------------- #
# Defensive behaviour — malformed / invalid input must not crash a task.
# --------------------------------------------------------------------------- #


def test_transform_tasks_are_defensive_against_malformed_input() -> None:
    """Null clinic id, wrong-typed cost, missing tags, and out-of-range clinic
    ids are dropped/coerced rather than raising — the board run must not fail
    because one event was malformed."""
    events = [
        # clinic_id is None → row dropped
        _event("bad-1", "inbound_order_created", clinic_id=None, unit_cost=99, quantity=1),
        # clinic_id out of the valid 1..12 range → row dropped
        _event("bad-2", "inbound_order_created", clinic_id="99", unit_cost=99, quantity=1),
        # unit_cost is a non-numeric string → coerced to 0.0, no crash
        _event("bad-3", "inbound_order_created", unit_cost="not-a-number", quantity=5),
        # tags missing entirely → row dropped (no clinic/country)
        {
            "event_id": "bad-4",
            "timestamp": "2026-07-10T09:00:00Z",
            "event_type": "inbound_order_created",
            "tags": None,
        },
        # one clean event so we can assert the surviving value
        _event("ok-1", "inbound_order_created", unit_cost=10, quantity=2),
    ]

    result = transform_supply_cost_per_clinic.fn(events, JULY)

    # bad-3 contributes 0 (coerced), the malformed rows are dropped, only the
    # clean event (10 * 2 = 20) remains for clinic 3.
    assert result == {("3", "US"): 20.0}


def test_empty_input_returns_empty_result() -> None:
    """No events → each transform task returns an empty mapping (a true zero,
    distinct from a run that never happened)."""
    assert transform_supply_cost_per_clinic.fn([], JULY) == {}
    assert transform_supply_consumption_volume.fn([], JULY) == {}
    assert transform_critical_stockout_frequency.fn([], JULY) == {}
    assert transform_expiry_risk_count.fn([], JULY) == {}


# --------------------------------------------------------------------------- #
# Cross-cutting transform behaviour.
# --------------------------------------------------------------------------- #


def test_duplicate_event_ids_are_deduped_before_counting() -> None:
    """A client retry that resends the same eventId must not inflate a count."""
    events = [
        _event("out-dup", "outbound_order_created", timestamp="2026-07-10T09:00:00Z"),
        _event("out-dup", "outbound_order_created", timestamp="2026-07-10T09:00:00.300Z"),
        _event("out-2", "outbound_order_created"),
    ]

    result = transform_supply_consumption_volume.fn(events, JULY)

    # 3 rows in, but two share event_id "out-dup" → counted once → total 2.
    assert result == {("3", "US"): 2}


def test_currency_and_country_split_us_usd_uk_gbp() -> None:
    """Composed rows keep US (USD) and UK (GBP) as separate clinic rows with the
    correct currency — never summed together."""
    events = [
        _event("us-in", "inbound_order_created", clinic_id="3", country="US",
               unit_cost=10, quantity=1),
        _event("uk-in", "inbound_order_created", clinic_id="7", country="UK",
               unit_cost=20, quantity=1),
    ]

    rows = aggregate_monthly_clinic_kpis(events, JULY)
    by_clinic = {row["clinic_id"]: row for row in rows}

    assert by_clinic["3"]["currency"] == "USD"
    assert by_clinic["3"]["total_supply_cost"] == 10.0
    assert by_clinic["7"]["currency"] == "GBP"
    assert by_clinic["7"]["total_supply_cost"] == 20.0


def test_events_outside_target_month_are_excluded() -> None:
    """Only events whose UTC timestamp falls in the target month are counted."""
    events = [
        _event("jul", "outbound_order_created", timestamp="2026-07-31T23:59:00Z"),
        _event("aug", "outbound_order_created", timestamp="2026-08-01T00:00:00Z"),
        _event("jun", "outbound_order_created", timestamp="2026-06-30T23:59:00Z"),
    ]

    result = transform_supply_consumption_volume.fn(events, JULY)

    assert result == {("3", "US"): 1}


def test_iso_timestamps_with_and_without_microseconds_are_kept() -> None:
    """Live ingest uses fractional seconds; seed rows often do not.

    Pandas to_datetime infers a format from the first rows unless ISO8601 is
    forced — mixed precision would otherwise drop the live inbound (cost 0).
    """
    events = [
        _event(
            "seed-in",
            "inbound_order_created",
            timestamp="2026-07-05T12:01:00+00:00",
            unit_cost=1,
            quantity=1,
        ),
        _event(
            "live-in",
            "inbound_order_created",
            timestamp="2026-07-12T14:43:23.642000+00:00",
            unit_cost=12.50,
            quantity=4,
        ),
        _event(
            "live-out",
            "outbound_order_created",
            timestamp="2026-07-12T14:44:01.255000+00:00",
        ),
    ]

    rows = aggregate_monthly_clinic_kpis(events, JULY)
    assert len(rows) == 1
    assert rows[0]["clinic_id"] == "3"
    assert rows[0]["total_supply_cost"] == 51.0
    assert rows[0]["supply_consumption_count"] == 1
