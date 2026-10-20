"""Tests for the agent's MCP client (`data.pipelines.mcp_client`).

MCP is the single transport: the client must never return ``None``. Every call
answers with the shared tool models — success, honest ``unavailable`` on
transport/config/parse failures, ``auth`` on a scope denial, ``invalid_input``
without arguments — so the graph always has a contract payload.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from data.pipelines import mcp_client
from data.pipelines.agent_tools import (
    INCIDENT_TOOL_AUTH_MESSAGE,
    INCIDENT_TOOL_FALLBACK,
    INVENTORY_TOOL_FALLBACK,
    IncidentToolInput,
    InventoryToolInput,
)


@pytest.fixture
def mcp_url(monkeypatch) -> str:
    url = "http://127.0.0.1:8100/mcp"
    monkeypatch.setenv("MCP_SERVER_URL", url)
    return url


def _incident_ok() -> str:
    return json.dumps(
        {
            "ok": True,
            "incidents": [
                {
                    "id": 7,
                    "title": "Printer offline",
                    "description": "d",
                    "category": "it_system",
                    "status": "open",
                    "origin": "internal",
                    "branch": "central",
                    "created_at": "",
                    "updated_at": "",
                }
            ],
            "error": None,
            "message": None,
        }
    )


def _inventory_ok() -> str:
    return json.dumps(
        {
            "ok": True,
            "products": [
                {
                    "id": 3,
                    "name": "Nitrile gloves",
                    "sku": "HCR-PPE-001",
                    "category": "ppe",
                    "unit": "box",
                    "country": "US",
                    "current_stock": 120,
                }
            ],
            "error": None,
            "message": None,
        }
    )


def _capture(monkeypatch, text: str | None) -> list[tuple[str, dict]]:
    calls: list[tuple[str, dict]] = []

    async def _fake(tool_name: str, arguments: dict):
        calls.append((tool_name, arguments))
        return text

    monkeypatch.setattr(mcp_client, "_call_tool", _fake)
    return calls


# --- Gating: disabled transport answers honestly, never ``None`` ---


def test_transport_disabled_returns_unavailable_without_calling_mcp(
    monkeypatch,
) -> None:
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)

    async def _unexpected(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("MCP must not be called when disabled")

    monkeypatch.setattr(mcp_client, "_call_tool", _unexpected)

    assert mcp_client.is_enabled() is False
    incident = mcp_client.lookup_incident_via_mcp(IncidentToolInput(ticket_id=7))
    assert incident.ok is False
    assert incident.error == "unavailable"
    assert incident.message == INCIDENT_TOOL_FALLBACK

    inventory = mcp_client.lookup_inventory_via_mcp(InventoryToolInput(sku="X"))
    assert inventory.ok is False
    assert inventory.error == "unavailable"
    assert inventory.message == INVENTORY_TOOL_FALLBACK


def test_missing_agent_credentials_returns_unavailable_without_raising(
    monkeypatch, mcp_url
) -> None:
    monkeypatch.delenv("AGENT_TOOL_CLIENT_ID", raising=False)
    monkeypatch.delenv("AGENT_TOOL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("AGENT_TOOL_CLIENT_SECRET_FILE", raising=False)

    assert mcp_client.is_enabled() is True
    result = mcp_client.lookup_incident_via_mcp(IncidentToolInput(ticket_id=7))
    assert result.ok is False
    assert result.error == "unavailable"


# --- Connection config: audience + Authorization header ---


def test_connection_carries_audience_and_bearer_header(monkeypatch, mcp_url) -> None:
    monkeypatch.setenv("MCP_RESOURCE_URL", "http://public.example/mcp")
    seen: dict = {}

    def _token(**kwargs) -> str:
        seen.update(kwargs)
        return "agent-jwt"

    monkeypatch.setattr(mcp_client, "get_service_token", _token)

    connection = mcp_client._connection()

    assert connection is not None
    assert connection["transport"] == "streamable_http"
    assert connection["url"] == mcp_url
    assert connection["headers"] == {"Authorization": "Bearer agent-jwt"}
    # RFC 8707: the minted token must carry the MCP resource as ``aud``.
    assert seen == {"audience": "http://public.example/mcp"}


def test_resource_url_defaults_and_env_override(monkeypatch) -> None:
    monkeypatch.delenv("MCP_RESOURCE_URL", raising=False)
    assert mcp_client.resource_url() == "http://localhost:8100/mcp"

    monkeypatch.setenv("MCP_RESOURCE_URL", "http://localhost:8100/mcp/")
    assert mcp_client.resource_url() == "http://localhost:8100/mcp"


def test_timeout_is_explicit_and_numeric(monkeypatch) -> None:
    assert mcp_client.MCP_TOOL_TIMEOUT_SECONDS == 10.0

    monkeypatch.setenv("MCP_TOOL_TIMEOUT_SECONDS", "3.5")
    assert mcp_client.tool_timeout_seconds() == 3.5

    monkeypatch.setenv("MCP_TOOL_TIMEOUT_SECONDS", "not-a-number")
    assert mcp_client.tool_timeout_seconds() == 10.0


# --- Tool routing matches the agent contract ---


def test_ticket_id_routes_to_detail_tool(monkeypatch, mcp_url) -> None:
    calls = _capture(monkeypatch, _incident_ok())

    result = mcp_client.lookup_incident_via_mcp(IncidentToolInput(ticket_id=7))

    assert calls == [(mcp_client.TOOL_GET_INCIDENT_STATUS, {"ticket_id": 7})]
    assert result.ok is True
    assert result.incidents[0].id == 7


def test_filters_route_to_list_tool_and_empty_filters_skip_mcp(
    monkeypatch, mcp_url
) -> None:
    calls = _capture(monkeypatch, _incident_ok())

    result = mcp_client.lookup_incident_via_mcp(
        IncidentToolInput(status="open", branch="central")
    )

    assert calls == [
        (mcp_client.TOOL_LIST_INCIDENTS, {"status": "open", "branch": "central"})
    ]
    assert result.ok is True

    calls.clear()
    empty = mcp_client.lookup_incident_via_mcp(IncidentToolInput())
    assert calls == []
    assert empty.ok is False
    assert empty.error == "invalid_input"


def test_inventory_arguments_are_forwarded_and_empty_skipped(
    monkeypatch, mcp_url
) -> None:
    calls = _capture(monkeypatch, _inventory_ok())

    result = mcp_client.lookup_inventory_via_mcp(
        InventoryToolInput(sku="HCR-PPE-001", name_query=None)
    )

    assert calls == [(mcp_client.TOOL_GET_INVENTORY_STOCK, {"sku": "HCR-PPE-001"})]
    assert result.ok is True
    assert result.products[0].sku == "HCR-PPE-001"

    calls.clear()
    empty = mcp_client.lookup_inventory_via_mcp(InventoryToolInput())
    assert calls == []
    assert empty.ok is False
    assert empty.error == "invalid_input"


# --- Failure honesty: contract payload on every path ---


def test_mcp_transport_failure_returns_honest_unavailable(monkeypatch, mcp_url) -> None:
    async def _boom(tool_name: str, arguments: dict):
        raise ConnectionError("mcp down")

    monkeypatch.setattr(mcp_client, "_call_tool", _boom)

    result = mcp_client.lookup_incident_via_mcp(IncidentToolInput(ticket_id=7))
    assert result.ok is False
    assert result.error == "unavailable"
    assert result.message == INCIDENT_TOOL_FALLBACK


def test_non_contract_payload_returns_honest_unavailable(monkeypatch, mcp_url) -> None:
    _capture(monkeypatch, "not json at all")

    result = mcp_client.lookup_incident_via_mcp(IncidentToolInput(ticket_id=7))
    assert result.ok is False
    assert result.error == "unavailable"


def test_scope_denial_exception_returns_auth_error(monkeypatch, mcp_url) -> None:
    """`handle_tool_errors=False` → the server denial raises; mapped to ``auth``."""

    async def _denied(tool_name: str, arguments: dict):
        raise Exception(
            "insufficient_scope: missing incidents:read for svc:langgraph-agent"
        )

    monkeypatch.setattr(mcp_client, "_call_tool", _denied)

    result = mcp_client.lookup_incident_via_mcp(IncidentToolInput(ticket_id=7))
    assert result.ok is False
    assert result.error == "auth"
    assert result.message == INCIDENT_TOOL_AUTH_MESSAGE

    inventory = mcp_client.lookup_inventory_via_mcp(
        InventoryToolInput(sku="HCR-PPE-001")
    )
    assert inventory.ok is False
    assert inventory.error == "auth"


def test_scope_denial_text_as_payload_is_not_a_contract(monkeypatch, mcp_url) -> None:
    _capture(
        monkeypatch,
        "Error executing tool get_incident_status: insufficient_scope: missing incidents:read",
    )

    result = mcp_client.lookup_incident_via_mcp(IncidentToolInput(ticket_id=7))
    assert result.ok is False
    assert result.error == "unavailable"


def test_honest_tool_error_payload_is_passed_through(monkeypatch, mcp_url) -> None:
    """A contract-shaped failure is data, not a transport problem."""
    _capture(
        monkeypatch,
        json.dumps(
            {
                "ok": False,
                "incidents": [],
                "error": "not_found",
                "message": "I could not find that ticket in the incident manager.",
            }
        ),
    )

    result = mcp_client.lookup_incident_via_mcp(IncidentToolInput(ticket_id=404))

    assert result.ok is False and result.error == "not_found"


# --- Content extraction (adapters return content blocks) ---


def test_extract_text_handles_adapters_shapes() -> None:
    assert mcp_client._extract_text("plain") == "plain"
    assert mcp_client._extract_text(
        [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]
    ) == "a\nb"
    assert mcp_client._extract_text([{"type": "image", "data": "..."}]) is None
    assert mcp_client._extract_text(("wrapped", None)) == "wrapped"
    assert mcp_client._extract_text(None) is None

    class _Message:
        content = [{"type": "text", "text": '{"ok": true}'}]

    assert mcp_client._extract_text(_Message()) == '{"ok": true}'


def test_sync_bridge_refuses_to_run_inside_an_event_loop() -> None:
    async def _inner() -> None:
        mcp_client._run(asyncio.sleep(0), 1.0)

    with pytest.raises(RuntimeError, match="synchronous-only"):
        asyncio.run(_inner())


def test_sync_bridge_runs_coroutines_on_its_own_loop() -> None:
    async def _value() -> int:
        return 42

    assert mcp_client._run(_value(), 5.0) == 42
