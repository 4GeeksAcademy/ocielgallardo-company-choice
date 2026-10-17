"""Unit tests for read-only agent tools over the live APIs (HTTP).

Offline: ``_http_get`` is monkeypatched — no backend required in CI.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import httpx  # noqa: E402

import data.pipelines.agent_tools as agent_tools  # noqa: E402
from data.pipelines.agent_tools import (  # noqa: E402
    INCIDENT_NOT_FOUND_MESSAGE,
    INCIDENT_TOOL_FALLBACK,
    INCIDENT_TOOL_TIMEOUT_SECONDS,
    INVENTORY_NOT_FOUND_MESSAGE,
    INVENTORY_TOOL_FALLBACK,
    INVENTORY_TOOL_TIMEOUT_SECONDS,
    IncidentToolInput,
    InventoryToolInput,
    format_incident_answer,
    format_inventory_answer,
    lookup_incident,
    lookup_inventory,
)


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=None, response=None
            )


def _incident_payload(ticket_id: int = 2) -> dict:
    return {
        "id": ticket_id,
        "title": "Patient not informed of appointment reschedule by clinic",
        "description": "Patient not informed of appointment reschedule by clinic",
        "category": "patient_experience",
        "status": "open",
        "origin": "customer",
        "branch": "london_west",
        "created_at": "2024-01-17T00:00:00Z",
        "updated_at": "2024-01-17T00:00:00Z",
    }


def test_timeouts_are_explicit_and_numeric() -> None:
    assert INCIDENT_TOOL_TIMEOUT_SECONDS == 5.0
    assert INVENTORY_TOOL_TIMEOUT_SECONDS == 5.0


def test_lookup_incident_by_id_calls_api_detail(monkeypatch) -> None:
    seen: dict = {}

    def _get(path: str, *, params=None, timeout_seconds: float):
        seen.update(path=path, params=params, timeout=timeout_seconds)
        assert timeout_seconds == 5.0
        return _FakeResponse(_incident_payload(2))

    monkeypatch.setattr(agent_tools, "_http_get", _get)

    out = lookup_incident(IncidentToolInput(ticket_id=2))

    assert seen["path"] == "/api/incidents/2"
    assert out.ok is True
    assert out.incidents[0].id == 2
    assert out.incidents[0].status == "open"
    assert "status=open" in format_incident_answer(out)


def test_lookup_incident_list_uses_filters(monkeypatch) -> None:
    seen: dict = {}

    def _get(path: str, *, params=None, timeout_seconds: float):
        seen.update(path=path, params=params)
        return _FakeResponse([_incident_payload(2)])

    monkeypatch.setattr(agent_tools, "_http_get", _get)

    out = lookup_incident(IncidentToolInput(status="open"))

    assert seen == {"path": "/api/incidents", "params": {"status": "open"}}
    assert out.ok is True


def test_lookup_incident_not_found_is_honest(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_tools, "_http_get", lambda *a, **k: _FakeResponse({}, 404)
    )

    out = lookup_incident(IncidentToolInput(ticket_id=99999))

    assert out.ok is False
    assert out.error == "not_found"
    assert format_incident_answer(out) == INCIDENT_NOT_FOUND_MESSAGE


def test_lookup_incident_timeout_returns_fallback(monkeypatch) -> None:
    def _slow(*args, **kwargs):
        raise httpx.TimeoutException("timed out", request=None)

    monkeypatch.setattr(agent_tools, "_http_get", _slow)

    out = lookup_incident(IncidentToolInput(ticket_id=2))

    assert out.ok is False
    assert out.error == "timeout"
    assert format_incident_answer(out) == INCIDENT_TOOL_FALLBACK


def test_lookup_incident_server_error_returns_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_tools, "_http_get", lambda *a, **k: _FakeResponse({}, 503)
    )

    out = lookup_incident(IncidentToolInput(ticket_id=2))

    assert out.ok is False
    assert out.error == "unavailable"
    assert format_incident_answer(out) == INCIDENT_TOOL_FALLBACK


def test_lookup_incident_invalid_input_without_id_or_filters() -> None:
    out = lookup_incident(IncidentToolInput())

    assert out.ok is False
    assert out.error == "invalid_input"


def test_lookup_inventory_by_sku_calls_products_api(monkeypatch) -> None:
    seen: dict = {}

    def _get(path: str, *, params=None, timeout_seconds: float):
        seen.update(path=path, timeout=timeout_seconds)
        return _FakeResponse(
            [
                {
                    "id": 1,
                    "name": "Guantes de nitrilo (caja de 100)",
                    "sku": "HCR-PPE-001",
                    "category": "ppe",
                    "unit": "box",
                    "country": "US",
                    "current_stock": 1289,
                },
                {
                    "id": 2,
                    "name": "Mascarilla quirúrgica (pack de 50)",
                    "sku": "HCR-PPE-002",
                    "category": "ppe",
                    "unit": "pack",
                    "country": "UK",
                    "current_stock": 1108,
                },
            ]
        )

    monkeypatch.setattr(agent_tools, "_http_get", _get)

    out = lookup_inventory(InventoryToolInput(sku="hcr-ppe-001"))

    assert seen["path"] == "/inventory/products"
    assert out.ok is True
    assert out.products[0].current_stock == 1289
    assert "1289" in format_inventory_answer(out)


def test_lookup_inventory_not_found(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_tools, "_http_get", lambda *a, **k: _FakeResponse([], 200)
    )

    out = lookup_inventory(InventoryToolInput(sku="HCR-NOPE-000"))

    assert out.ok is False
    assert out.error == "not_found"
    assert format_inventory_answer(out) == INVENTORY_NOT_FOUND_MESSAGE


def test_lookup_inventory_timeout_returns_fallback(monkeypatch) -> None:
    def _slow(*args, **kwargs):
        raise httpx.TimeoutException("timed out", request=None)

    monkeypatch.setattr(agent_tools, "_http_get", _slow)

    out = lookup_inventory(InventoryToolInput(sku="HCR-PPE-001"))

    assert out.ok is False
    assert out.error == "timeout"
    assert format_inventory_answer(out) == INVENTORY_TOOL_FALLBACK


def test_tools_are_read_only_get_only() -> None:
    """Static guard: tools must only ever issue HTTP GET (never write)."""
    source = Path(agent_tools.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "httpx.post",
        "httpx.patch",
        "httpx.put",
        "httpx.delete",
        ".post(",
        ".patch(",
        ".put(",
        ".delete(",
        "create_incident",
        "update_incident_status",
        "create_supply",
        "create_delivery",
        "create_consumption",
    ):
        assert forbidden not in source
    assert "_http_get" in source


def test_auth_comes_from_env_never_hardcoded(monkeypatch) -> None:
    """Static + runtime guard: Bearer token is read from env, not literals."""
    source = Path(agent_tools.__file__).read_text(encoding="utf-8")
    assert "AGENT_TOOL_API_TOKEN" in source
    assert "AGENT_TOOL_API_URL" in source

    monkeypatch.setenv("AGENT_TOOL_API_TOKEN", "secret-token")
    headers = agent_tools._auth_headers()
    assert headers == {"Authorization": "Bearer secret-token"}

    monkeypatch.delenv("AGENT_TOOL_API_TOKEN", raising=False)
    assert agent_tools._auth_headers() == {}
