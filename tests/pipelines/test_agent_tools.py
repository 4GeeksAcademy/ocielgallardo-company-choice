"""Unit tests for the shared tool contracts and answer formatters.

Offline and network-free by construction: this module holds models and
formatters only. A static guard proves the module contains no HTTP client, no
write verb, and no live lookup — the single MCP transport lives in
``data/pipelines/mcp_client.py`` (tested there) and the server-side read-only
tools live in ``mcps/incidents-inventory-mcp``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pydantic import ValidationError  # noqa: E402

import data.pipelines.agent_tools as agent_tools  # noqa: E402
from data.pipelines.agent_tools import (  # noqa: E402
    INCIDENT_NOT_FOUND_MESSAGE,
    INCIDENT_TOOL_AUTH_MESSAGE,
    INCIDENT_TOOL_FALLBACK,
    INVENTORY_NOT_FOUND_MESSAGE,
    INVENTORY_TOOL_AUTH_MESSAGE,
    INVENTORY_TOOL_FALLBACK,
    IncidentRecord,
    IncidentToolInput,
    IncidentToolOutput,
    InventoryRecord,
    InventoryToolInput,
    InventoryToolOutput,
    format_incident_answer,
    format_inventory_answer,
)


def _incident_ok() -> IncidentToolOutput:
    return IncidentToolOutput(
        ok=True,
        incidents=[
            IncidentRecord(
                id=2,
                title="Patient not informed of appointment reschedule by clinic",
                description="Patient not informed of appointment reschedule by clinic",
                category="patient_experience",
                status="open",
                origin="customer",
                branch="london_west",
                created_at="2024-01-17T00:00:00Z",
                updated_at="2024-01-17T00:00:00Z",
            )
        ],
    )


def _inventory_ok() -> InventoryToolOutput:
    return InventoryToolOutput(
        ok=True,
        products=[
            InventoryRecord(
                id=1,
                name="Guantes de nitrilo (caja de 100)",
                sku="HCR-PPE-001",
                category="ppe",
                unit="box",
                country="US",
                current_stock=1289,
            )
        ],
    )


# --- Incident contract ---


def test_incident_input_rejects_invalid_ticket_id() -> None:
    with pytest.raises(ValidationError):
        IncidentToolInput(ticket_id=0)
    assert IncidentToolInput().ticket_id is None


def test_incident_success_formats_deterministically() -> None:
    out = _incident_ok()

    answer = format_incident_answer(out)
    assert out.ok is True
    assert "Ticket 2" in answer
    assert "status=open" in answer
    assert "updated_at=2024-01-17T00:00:00Z" in answer


def test_incident_failure_returns_own_message() -> None:
    out = IncidentToolOutput(
        ok=False, error="unavailable", message=INCIDENT_TOOL_FALLBACK
    )
    assert format_incident_answer(out) == INCIDENT_TOOL_FALLBACK


def test_incident_empty_payload_is_not_found() -> None:
    assert (
        format_incident_answer(IncidentToolOutput(ok=True, incidents=[]))
        == INCIDENT_NOT_FOUND_MESSAGE
    )


def test_incident_messages_are_distinct() -> None:
    assert len(
        {
            INCIDENT_TOOL_FALLBACK,
            INCIDENT_NOT_FOUND_MESSAGE,
            INCIDENT_TOOL_AUTH_MESSAGE,
        }
    ) == 3


# --- Inventory contract ---


def test_inventory_input_rejects_invalid_supply_id() -> None:
    with pytest.raises(ValidationError):
        InventoryToolInput(supply_id=0)
    assert InventoryToolInput().sku is None


def test_inventory_success_formats_deterministically() -> None:
    out = _inventory_ok()

    answer = format_inventory_answer(out)
    assert out.ok is True
    assert "SKU HCR-PPE-001" in answer
    assert "current_stock=1289" in answer


def test_inventory_failure_returns_own_message() -> None:
    out = InventoryToolOutput(
        ok=False, error="unavailable", message=INVENTORY_TOOL_FALLBACK
    )
    assert format_inventory_answer(out) == INVENTORY_TOOL_FALLBACK


def test_inventory_empty_payload_is_not_found() -> None:
    assert (
        format_inventory_answer(InventoryToolOutput(ok=True, products=[]))
        == INVENTORY_NOT_FOUND_MESSAGE
    )


def test_inventory_messages_are_distinct() -> None:
    assert len(
        {
            INVENTORY_TOOL_FALLBACK,
            INVENTORY_NOT_FOUND_MESSAGE,
            INVENTORY_TOOL_AUTH_MESSAGE,
        }
    ) == 3


# --- Static guards: contracts only, no transport, no write verbs ---


def test_module_is_contract_only_without_http_or_writes() -> None:
    """Static guard: no HTTP client, no lookup, no write verb in this module."""
    source = Path(agent_tools.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "httpx",
        "requests",
        "urllib",
        "httpx.post",
        ".post(",
        ".patch(",
        ".put(",
        ".delete(",
        "_http_get",
        "_auth_headers",
        "get_service_token",
        "create_incident",
        "update_incident_status",
        "create_supply",
        "create_delivery",
        "create_consumption",
        "def lookup_incident",
        "def lookup_inventory",
    ):
        assert forbidden not in source, forbidden
    for required in ("IncidentToolInput", "IncidentToolOutput", "format_incident_answer",
                     "InventoryToolInput", "InventoryToolOutput", "format_inventory_answer"):
        assert required in source, required


def test_auth_comes_from_service_client_credentials_never_hardcoded() -> None:
    """Static guard: env-driven client credentials; legacy user JWT retired."""
    provider_source = (
        Path(agent_tools.__file__).parent / "service_token_provider.py"
    ).read_text(encoding="utf-8")

    assert "AGENT_TOOL_CLIENT_ID" in provider_source
    assert "AGENT_TOOL_CLIENT_SECRET" in provider_source
    assert "AGENT_TOOL_API_URL" in provider_source
    # Pasted user JWT mechanism fully removed (agent-graph.md §9.1).
    assert "AGENT_TOOL_API_TOKEN" not in provider_source
