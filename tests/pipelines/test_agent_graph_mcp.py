"""Graph-level tests for the single MCP transport (no fallback path).

MCP is the only way the graph reaches the incidents/inventory server. These
tests pin the node contract for every transport state: MCP answering, MCP
configured but failing, and MCP not configured at all. In every case the node
must emit a contract payload (never ``None``), keep the span contract
(``transport == "mcp"``), and answer honestly instead of inventing state —
there is no direct HTTP path left to fall back to.
"""

from __future__ import annotations

import pytest

import data.pipelines.mcp_client as mcp_client
from data.pipelines.agent_tools import (
    INCIDENT_TOOL_FALLBACK,
    IncidentRecord,
    IncidentToolInput,
    IncidentToolOutput,
    InventoryRecord,
    InventoryToolInput,
    InventoryToolOutput,
)
from data.pipelines.agent_graph import get_trace, run_agent

TICKET_QUESTION = "What is the status of ticket 2?"
STOCK_QUESTION = "Do we have stock of HCR-PPE-001?"


def _incident_output() -> IncidentToolOutput:
    return IncidentToolOutput(
        ok=True,
        incidents=[
            IncidentRecord(
                id=2,
                title="Patient not informed",
                description="Patient not informed",
                category="patient_experience",
                status="open",
                origin="customer",
                branch="london_west",
                created_at="2024-01-17T00:00:00Z",
                updated_at="2024-01-17T00:00:00Z",
            )
        ],
    )


def _inventory_output() -> InventoryToolOutput:
    return InventoryToolOutput(
        ok=True,
        products=[
            InventoryRecord(
                id=1,
                name="Nitrile gloves",
                sku="HCR-PPE-001",
                category="ppe",
                unit="box",
                country="US",
                current_stock=120,
            )
        ],
    )


def _span(trace: dict, node: str) -> dict:
    return next(span for span in trace["spans"] if span["node"] == node)


@pytest.fixture
def mcp_configured(monkeypatch) -> None:
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:8100/mcp")


def test_incident_question_uses_mcp(monkeypatch, mcp_configured) -> None:
    monkeypatch.setattr(
        mcp_client,
        "lookup_incident_via_mcp",
        lambda payload, **kw: _incident_output(),
    )

    result = run_agent(TICKET_QUESTION)
    trace = get_trace(result["trace_id"])

    assert "incidents" in trace["sources_used"]
    assert "open" in result["answer"]
    assert _span(trace, "lookup_incident")["output"]["transport"] == "mcp"
    assert _span(trace, "lookup_incident")["output"]["ok"] is True


def test_inventory_question_uses_mcp(monkeypatch, mcp_configured) -> None:
    monkeypatch.setattr(
        mcp_client,
        "lookup_inventory_via_mcp",
        lambda payload, **kw: _inventory_output(),
    )

    result = run_agent(STOCK_QUESTION)
    trace = get_trace(result["trace_id"])

    assert "inventory" in trace["sources_used"]
    assert "120" in result["answer"]
    assert _span(trace, "lookup_inventory")["output"]["transport"] == "mcp"


def test_mcp_failure_answers_honestly_without_any_other_transport(
    monkeypatch, mcp_configured
) -> None:
    """A failing MCP hop must not open a second path; the answer stays honest."""
    failed = IncidentToolOutput(
        ok=False, error="unavailable", message=INCIDENT_TOOL_FALLBACK
    )
    monkeypatch.setattr(
        mcp_client, "lookup_incident_via_mcp", lambda payload, **kw: failed
    )

    result = run_agent(TICKET_QUESTION)
    trace = get_trace(result["trace_id"])

    assert INCIDENT_TOOL_FALLBACK in result["answer"]
    assert _span(trace, "lookup_incident")["output"]["error"] == "unavailable"
    assert _span(trace, "lookup_incident")["output"]["transport"] == "mcp"
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "decide_route",
        "lookup_incident",
        "tool_fallback",
    ]


def test_real_client_without_server_url_returns_unavailable(monkeypatch) -> None:
    """Real client + no ``MCP_SERVER_URL`` → contract failure, never ``None``."""
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)

    result = mcp_client.lookup_incident_via_mcp(IncidentToolInput(ticket_id=2))
    assert result.ok is False
    assert result.error == "unavailable"

    inventory = mcp_client.lookup_inventory_via_mcp(
        InventoryToolInput(sku="HCR-PPE-001")
    )
    assert inventory.ok is False
    assert inventory.error == "unavailable"


def test_mcp_disabled_still_answers_honestly(monkeypatch) -> None:
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)

    result = run_agent(TICKET_QUESTION)
    trace = get_trace(result["trace_id"])

    assert INCIDENT_TOOL_FALLBACK in result["answer"]
    assert _span(trace, "lookup_incident")["output"]["error"] == "unavailable"
    assert _span(trace, "lookup_incident")["output"]["transport"] == "mcp"
    assert [span["node"] for span in trace["spans"]] == [
        "receive",
        "decide_route",
        "lookup_incident",
        "tool_fallback",
    ]
