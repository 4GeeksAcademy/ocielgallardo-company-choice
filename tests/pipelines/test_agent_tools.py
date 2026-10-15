"""Unit tests for read-only agent tools (incident lookup).

Offline: the domain layer is monkeypatched — no TinyDB required in CI.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

import data.pipelines.agent_tools as agent_tools  # noqa: E402
from data.pipelines.agent_tools import (  # noqa: E402
    INCIDENT_NOT_FOUND_MESSAGE,
    INCIDENT_TOOL_FALLBACK,
    INCIDENT_TOOL_TIMEOUT_SECONDS,
    IncidentToolInput,
    format_incident_answer,
    lookup_incident,
)


def _fake_incident(ticket_id: int = 482) -> SimpleNamespace:
    return SimpleNamespace(
        id=ticket_id,
        title="Printer offline at front desk",
        description="Cannot print labels",
        category=SimpleNamespace(value="it_system"),
        status=SimpleNamespace(value="in_progress"),
        origin=SimpleNamespace(value="branch"),
        branch=SimpleNamespace(value="austin_north"),
        created_at="2026-01-10T12:00:00Z",
        updated_at="2026-01-11T09:30:00Z",
    )


def test_incident_tool_timeout_constant_is_numeric_and_positive() -> None:
    assert isinstance(INCIDENT_TOOL_TIMEOUT_SECONDS, float)
    assert INCIDENT_TOOL_TIMEOUT_SECONDS == 5.0


def test_lookup_incident_by_id_reads_real_domain(monkeypatch) -> None:
    calls: list[int] = []

    def _get(incident_id: int):
        calls.append(incident_id)
        return _fake_incident(incident_id)

    monkeypatch.setattr(
        "services.app.domain.incident_manager_service.get_incident", _get
    )

    out = lookup_incident(IncidentToolInput(ticket_id=482))

    assert calls == [482]
    assert out.ok is True
    assert out.error is None
    assert len(out.incidents) == 1
    assert out.incidents[0].id == 482
    assert out.incidents[0].status == "in_progress"
    assert out.incidents[0].category == "it_system"
    assert "482" in format_incident_answer(out)
    assert "in_progress" in format_incident_answer(out)


def test_lookup_incident_not_found_is_honest(monkeypatch) -> None:
    from services.app.domain.incident_manager_service import IncidentNotFoundError

    def _missing(incident_id: int):
        raise IncidentNotFoundError("Incident not found")

    monkeypatch.setattr(
        "services.app.domain.incident_manager_service.get_incident", _missing
    )

    out = lookup_incident(IncidentToolInput(ticket_id=99999))

    assert out.ok is False
    assert out.error == "not_found"
    assert out.incidents == []
    assert format_incident_answer(out) == INCIDENT_NOT_FOUND_MESSAGE


def test_lookup_incident_timeout_returns_fallback(monkeypatch) -> None:
    def _slow(payload):
        time.sleep(0.3)
        return []

    monkeypatch.setattr(agent_tools, "_fetch_incidents", _slow)

    out = lookup_incident(IncidentToolInput(ticket_id=1), timeout_seconds=0.05)

    assert out.ok is False
    assert out.error == "timeout"
    assert format_incident_answer(out) == INCIDENT_TOOL_FALLBACK


def test_lookup_incident_service_error_returns_fallback(monkeypatch) -> None:
    def _boom(payload):
        raise RuntimeError("TinyDB locked")

    monkeypatch.setattr(agent_tools, "_fetch_incidents", _boom)

    out = lookup_incident(IncidentToolInput(ticket_id=1))

    assert out.ok is False
    assert out.error == "unavailable"
    assert format_incident_answer(out) == INCIDENT_TOOL_FALLBACK


def test_lookup_incident_invalid_input_without_id_or_filters() -> None:
    out = lookup_incident(IncidentToolInput())

    assert out.ok is False
    assert out.error == "invalid_input"
    assert format_incident_answer(out) == INCIDENT_TOOL_FALLBACK


def test_lookup_incident_list_filters_are_read_only(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _list(**kwargs):
        seen.update(kwargs)
        return [_fake_incident(10)]

    monkeypatch.setattr(
        "services.app.domain.incident_manager_service.list_incidents", _list
    )

    out = lookup_incident(IncidentToolInput(status="open", category="it_system"))

    assert seen == {
        "status": "open",
        "origin": None,
        "branch": None,
        "category": "it_system",
    }
    assert out.ok is True
    assert out.incidents[0].id == 10


def test_incident_tool_is_read_only_module() -> None:
    """Static guard: this module must not call write APIs on the manager."""
    source = Path(agent_tools.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "create_incident",
        "update_incident_status",
        "insert_seed_incident",
        "create_supply",
        "create_delivery",
        "create_consumption",
    ):
        assert forbidden not in source


# --- Inventory tool ---


def _fake_supply(sku: str = "HCR-PPE-001") -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        name="Guantes de nitrilo (caja de 100)",
        sku=sku,
        category="ppe",
        unit="box",
        country="US",
        current_stock=55,
    )


def test_inventory_tool_timeout_constant_is_numeric() -> None:
    assert agent_tools.INVENTORY_TOOL_TIMEOUT_SECONDS == 5.0


def test_lookup_inventory_by_sku_reads_domain(monkeypatch) -> None:
    def _list(session):
        return [_fake_supply(), _fake_supply("HCR-PPE-002")]

    monkeypatch.setattr(agent_tools, "_fetch_inventory", None)

    def _fetch(payload):
        assert payload.sku == "HCR-PPE-001"
        return [
            agent_tools.InventoryRecord(
                id=1,
                name="Guantes de nitrilo (caja de 100)",
                sku="HCR-PPE-001",
                category="ppe",
                unit="box",
                country="US",
                current_stock=55,
            )
        ]

    monkeypatch.setattr(agent_tools, "_fetch_inventory", _fetch)

    out = agent_tools.lookup_inventory(
        agent_tools.InventoryToolInput(sku="HCR-PPE-001")
    )

    assert out.ok is True
    assert out.products[0].current_stock == 55
    assert "55" in agent_tools.format_inventory_answer(out)
    assert "HCR-PPE-001" in agent_tools.format_inventory_answer(out)


def test_lookup_inventory_timeout_returns_fallback(monkeypatch) -> None:
    def _slow(payload):
        time.sleep(0.3)
        return []

    monkeypatch.setattr(agent_tools, "_fetch_inventory", _slow)

    out = agent_tools.lookup_inventory(
        agent_tools.InventoryToolInput(sku="HCR-PPE-001"),
        timeout_seconds=0.05,
    )

    assert out.ok is False
    assert out.error == "timeout"
    assert (
        agent_tools.format_inventory_answer(out)
        == agent_tools.INVENTORY_TOOL_FALLBACK
    )


def test_lookup_inventory_not_found(monkeypatch) -> None:
    monkeypatch.setattr(agent_tools, "_fetch_inventory", lambda payload: [])

    out = agent_tools.lookup_inventory(
        agent_tools.InventoryToolInput(sku="HCR-NOPE-000")
    )

    assert out.ok is False
    assert out.error == "not_found"
    assert (
        agent_tools.format_inventory_answer(out)
        == agent_tools.INVENTORY_NOT_FOUND_MESSAGE
    )
