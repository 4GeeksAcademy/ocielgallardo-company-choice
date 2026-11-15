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
    format_not_stocked_answer,
    inventory_lookup_complete,
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
    assert "Ticket #2" in answer
    assert "is currently open" in answer
    assert "last updated on Jan 17, 2024" in answer
    assert "status=" not in answer and "updated_at=" not in answer


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
    assert "We currently have 1,289 boxes of" in answer
    assert "current_stock=" not in answer


def test_inventory_failure_returns_own_message() -> None:
    out = InventoryToolOutput(
        ok=False, error="unavailable", message=INVENTORY_TOOL_FALLBACK
    )
    assert format_inventory_answer(out) == INVENTORY_TOOL_FALLBACK


def test_inventory_empty_payload_is_a_normal_not_stocked_answer() -> None:
    answer = format_inventory_answer(InventoryToolOutput(ok=True, products=[]))
    assert answer == format_not_stocked_answer(None)
    assert answer.startswith("We don't currently have that product in stock.")
    assert "I could not find that product" not in answer
    assert "SKU " not in answer
    assert "Products currently in inventory" not in answer


def test_inventory_miss_is_a_short_not_stocked_answer() -> None:
    catalogue = [
        InventoryRecord(
            id=1, name="Guantes de nitrilo (caja de 100)", sku="HCR-PPE-001",
            category="ppe", unit="box", country="US", current_stock=1289,
        ),
        InventoryRecord(
            id=2, name="Mascarilla quirúrgica (pack de 50)", sku="HCR-PPE-002",
            category="ppe", unit="pack", country="UK", current_stock=1108,
        ),
    ]
    out = InventoryToolOutput(
        ok=True, products=[], catalogue=catalogue, queried_name="syringes"
    )
    answer = format_inventory_answer(out)
    assert answer == (
        "We don't currently have syringes in stock. "
        "You can search the inventory page manually."
    )
    assert "Guantes de nitrilo" not in answer
    assert "SKU " not in answer
    assert "Products currently in inventory" not in answer
    assert "I could not find" not in answer
    assert format_not_stocked_answer("syringes", catalogue) == answer
    assert inventory_lookup_complete(out) is True
    # Legacy not_found payloads are also a complete, normal answer.
    legacy = InventoryToolOutput(ok=False, error="not_found", queried_name="needles")
    assert inventory_lookup_complete(legacy) is True
    assert format_inventory_answer(legacy) == format_not_stocked_answer("needles")


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


# --- Natural-language rendering of tool facts ---


def test_describe_incident_reads_as_plain_english() -> None:
    from data.pipelines.agent_tools import IncidentRecord, describe_incident

    record = IncidentRecord(
        id=8,
        title="Duplicate charge for the same consultation detected",
        description="",
        category="billing_error",
        status="open",
        origin="customer",
        branch="miami_brickell",
        updated_at="2024-01-20T00:00:00Z",
    )
    assert describe_incident(record) == (
        "Ticket #8 (\u201cDuplicate charge for the same consultation detected\u201d) "
        "is currently open. It is a billing error reported by a customer at the "
        "Miami Brickell branch. It was last updated on Jan 20, 2024."
    )
    in_progress = record.model_copy(
        update={"status": "in_progress", "category": "it_system", "origin": "internal"}
    )
    text = describe_incident(in_progress)
    assert "is currently in progress" in text
    assert "an IT system issue raised internally" in text


def test_describe_stock_pluralizes_units_and_handles_zero() -> None:
    from data.pipelines.agent_tools import InventoryRecord, describe_stock

    base = InventoryRecord(
        id=1, name="Solución salina 0,9% 500ml", sku="HCR-MED-001",
        category="medications", unit="vial", country="UK", current_stock=1,
    )
    assert describe_stock(base) == (
        "We currently have 1 vial of Solución salina 0,9% 500ml (SKU HCR-MED-001) "
        "in stock in the UK."
    )
    assert "2,500 vials" in describe_stock(base.model_copy(update={"current_stock": 2500}))
    assert describe_stock(base.model_copy(update={"current_stock": 0})) == (
        "Solución salina 0,9% 500ml (SKU HCR-MED-001) is out of stock in the UK."
    )
