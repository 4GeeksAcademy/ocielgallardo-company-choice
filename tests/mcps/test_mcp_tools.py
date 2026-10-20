"""Behaviour tests for the MCP tools (transport + contract + failure honesty).

The backend is monkeypatched at ``backend_client`` so these tests cover the MCP
layer only: tool discovery, per-tool scope enforcement, payload contract, and
the failure taxonomy the agent depends on (``not_found`` / ``unavailable`` /
``invalid_input`` / ``auth``).
"""

from __future__ import annotations

import json

import pytest

from tests.mcps.mcp_helpers import (
    LIST_TOOLS,
    call_tool,
    mint_token,
    post_json_rpc,
    tool_error_text,
    tool_payload,
)

from incidents_inventory_mcp import backend_client

READ_TOKEN = mint_token(["incidents:read", "inventory:read"])
WRITE_TOKEN = mint_token(["incidents:read", "incidents:write", "inventory:read"])

INCIDENT_ROW = {
    "id": 7,
    "title": "Printer offline",
    "description": "Front desk printer unreachable",
    "category": "it_system",
    "status": "open",
    "origin": "internal",
    "branch": "central",
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00",
}
PRODUCT_ROW = {
    "id": 3,
    "name": "Nitrile gloves",
    "sku": "HCR-PPE-001",
    "category": "ppe",
    "unit": "box",
    "country": "US",
    "current_stock": 120,
}


def _names(payload: dict) -> set[str]:
    return {tool["name"] for tool in payload["result"]["tools"]}


EXPECTED_TOOL_NAMES = {
    "get_incident_status",
    "list_incidents",
    "create_incident",
    "update_incident_status",
    "get_inventory_stock",
    "update_inventory_stock",
}


# --- Discovery ---


def test_tools_list_exposes_only_reviewed_tools(app_client) -> None:
    _, payload = post_json_rpc(app_client, LIST_TOOLS, READ_TOKEN)

    assert _names(payload) == EXPECTED_TOOL_NAMES


def test_tools_list_schema_declares_required_arguments(app_client) -> None:
    _, payload = post_json_rpc(app_client, LIST_TOOLS, READ_TOKEN)
    tools = {tool["name"]: tool for tool in payload["result"]["tools"]}

    assert tools["get_incident_status"]["inputSchema"]["required"] == ["ticket_id"]
    assert set(tools["create_incident"]["inputSchema"]["properties"]) == {
        "title",
        "description",
        "category",
        "origin",
        "branch",
    }
    assert tools["list_incidents"]["inputSchema"].get("required", []) == []


def test_every_tool_advertises_an_output_schema(app_client) -> None:
    """Structured output: every tool declares the contract model in tools/list."""
    _, payload = post_json_rpc(app_client, LIST_TOOLS, READ_TOKEN)

    for tool in payload["result"]["tools"]:
        schema = tool.get("outputSchema")
        assert schema, tool["name"]
        assert "ok" in schema.get("properties", {}), tool["name"]


def test_successful_call_returns_structured_content(app_client, monkeypatch) -> None:
    async def _fake(ticket_id: int) -> dict:
        return dict(INCIDENT_ROW)

    monkeypatch.setattr(backend_client, "get_incident", _fake)

    payload = call_tool(
        app_client, "get_incident_status", {"ticket_id": 7}, READ_TOKEN
    )

    structured = payload["result"].get("structuredContent")
    assert structured is not None, payload
    assert structured["ok"] is True
    assert structured["incidents"] == [INCIDENT_ROW]


def test_unknown_tool_is_rejected_by_the_protocol(app_client) -> None:
    payload = call_tool(
        app_client, "delete_all_incidents", {}, WRITE_TOKEN
    )

    assert "Unknown tool" in tool_error_text(payload)


def test_update_inventory_stock_refuses_explicitly_without_backend(
    app_client, monkeypatch
) -> None:
    """Read-only policy: the write tool exists to refuse, not to proxy."""
    async def _unexpected(*args, **kwargs):
        raise AssertionError("read-only policy must never reach the backend")

    monkeypatch.setattr(backend_client, "get_products", _unexpected)
    monkeypatch.setattr(backend_client, "get_product", _unexpected)

    payload = call_tool(
        app_client,
        "update_inventory_stock",
        {"supply_id": 3, "quantity_change": -4, "reason": "restock"},
        WRITE_TOKEN,
    )

    message = tool_error_text(payload)
    assert "inventory_write_denied" in message
    assert "human operator" in message


# --- Audit trail ---


def _audit_lines(caplog) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.getMessage().startswith("mcp_tool ")
    ]


def test_successful_call_is_audited(app_client, monkeypatch, caplog) -> None:
    async def _fake(ticket_id: int) -> dict:
        return dict(INCIDENT_ROW)

    monkeypatch.setattr(backend_client, "get_incident", _fake)

    with caplog.at_level("INFO", logger="incidents_inventory_mcp.server"):
        call_tool(app_client, "get_incident_status", {"ticket_id": 7}, READ_TOKEN)

    lines = _audit_lines(caplog)
    assert lines, "no mcp_tool audit line was logged"
    line = lines[-1]
    assert "tool=get_incident_status" in line
    assert "client=mcp-server" in line
    assert "result=ok" in line
    assert "ms=" in line


def test_scope_denial_is_audited(app_client, caplog) -> None:
    with caplog.at_level("INFO", logger="incidents_inventory_mcp.server"):
        call_tool(
            app_client,
            "create_incident",
            {
                "title": "t",
                "description": "d",
                "category": "it_system",
                "origin": "internal",
                "branch": "central",
            },
            READ_TOKEN,
        )

    lines = _audit_lines(caplog)
    assert lines, "no mcp_tool audit line was logged"
    line = lines[-1]
    assert "tool=create_incident" in line
    assert "result=denied_scope" in line


# --- Scope enforcement per tool ---


@pytest.mark.parametrize(
    ("tool_name", "arguments", "missing_scope"),
    [
        ("create_incident", {
            "title": "t",
            "description": "d",
            "category": "it_system",
            "origin": "internal",
            "branch": "central",
        }, "incidents:write"),
        ("update_incident_status", {"ticket_id": 7, "status": "resolved"}, "incidents:write"),
    ],
)
def test_write_tools_deny_read_only_tokens(
    app_client, monkeypatch, tool_name, arguments, missing_scope
) -> None:
    async def _unexpected(*args, **kwargs):
        raise AssertionError("backend must not be called without the write scope")

    monkeypatch.setattr(backend_client, "create_incident", _unexpected)
    monkeypatch.setattr(backend_client, "update_incident_status", _unexpected)

    payload = call_tool(app_client, tool_name, arguments, READ_TOKEN)

    message = tool_error_text(payload)
    assert "insufficient_scope" in message
    assert missing_scope in message


def test_inventory_tool_denies_token_without_inventory_scope(app_client, monkeypatch) -> None:
    async def _unexpected(*args, **kwargs):
        raise AssertionError("backend must not be called without inventory:read")

    monkeypatch.setattr(backend_client, "get_products", _unexpected)

    payload = call_tool(app_client, "get_inventory_stock", {"sku": "HCR-PPE-001"}, mint_token(["incidents:read"]))

    assert "insufficient_scope" in tool_error_text(payload)


# --- Contract shape on success ---


def test_get_incident_status_returns_contract_payload(app_client, monkeypatch) -> None:
    async def _fake(ticket_id: int) -> dict:
        assert ticket_id == 7
        return dict(INCIDENT_ROW)

    monkeypatch.setattr(backend_client, "get_incident", _fake)

    payload = tool_payload(call_tool(app_client, "get_incident_status", {"ticket_id": 7}, READ_TOKEN))

    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["incidents"] == [INCIDENT_ROW]


def test_create_incident_sends_reviewed_body(app_client, monkeypatch) -> None:
    captured: dict = {}

    async def _fake(body: dict) -> dict:
        captured.update(body)
        return {**INCIDENT_ROW, **body}

    monkeypatch.setattr(backend_client, "create_incident", _fake)

    payload = tool_payload(
        call_tool(
            app_client,
            "create_incident",
            {
                "title": "Printer offline",
                "description": "Front desk printer unreachable",
                "category": "it_system",
                "origin": "internal",
                "branch": "central",
            },
            WRITE_TOKEN,
        )
    )

    assert captured == {
        "title": "Printer offline",
        "description": "Front desk printer unreachable",
        "category": "it_system",
        "origin": "internal",
        "branch": "central",
    }
    assert payload["ok"] is True


def test_list_incidents_forwards_only_provided_filters(app_client, monkeypatch) -> None:
    captured: dict = {}

    async def _fake(params: dict) -> list[dict]:
        captured.update(params)
        return [INCIDENT_ROW]

    monkeypatch.setattr(backend_client, "get_incidents", _fake)

    payload = tool_payload(
        call_tool(app_client, "list_incidents", {"status": "open", "branch": "central"}, READ_TOKEN)
    )

    assert captured == {"status": "open", "branch": "central"}
    assert payload["incidents"] == [INCIDENT_ROW]


def test_list_incidents_without_filters_is_invalid_input(app_client, monkeypatch) -> None:
    async def _unexpected(*args, **kwargs):
        raise AssertionError("unfiltered listing must not reach the backend")

    monkeypatch.setattr(backend_client, "get_incidents", _unexpected)

    payload = tool_payload(call_tool(app_client, "list_incidents", {}, READ_TOKEN))

    assert payload["ok"] is False
    assert payload["error"] == "invalid_input"


# --- Inventory is read-only and filters like the agent contract ---


def test_inventory_sku_filter_is_exact_and_case_insensitive(app_client, monkeypatch) -> None:
    async def _fake() -> list[dict]:
        return [dict(PRODUCT_ROW), {**PRODUCT_ROW, "id": 4, "sku": "HCR-PPE-999"}]

    monkeypatch.setattr(backend_client, "get_products", _fake)

    payload = tool_payload(
        call_tool(app_client, "get_inventory_stock", {"sku": "hcr-ppe-001"}, READ_TOKEN)
    )

    assert [item["sku"] for item in payload["products"]] == ["HCR-PPE-001"]


def test_inventory_name_query_is_substring_and_not_found_is_honest(
    app_client, monkeypatch
) -> None:
    async def _fake() -> list[dict]:
        return [dict(PRODUCT_ROW)]

    monkeypatch.setattr(backend_client, "get_products", _fake)

    hit = tool_payload(
        call_tool(app_client, "get_inventory_stock", {"name_query": "glove"}, READ_TOKEN)
    )
    assert [item["id"] for item in hit["products"]] == [3]

    miss = tool_payload(
        call_tool(app_client, "get_inventory_stock", {"name_query": "mask"}, READ_TOKEN)
    )
    assert miss["ok"] is False
    assert miss["error"] == "not_found"


def test_inventory_tool_without_arguments_is_invalid_input(app_client, monkeypatch) -> None:
    async def _unexpected(*args, **kwargs):
        raise AssertionError("argument-less inventory call must not reach the backend")

    monkeypatch.setattr(backend_client, "get_products", _unexpected)

    payload = tool_payload(call_tool(app_client, "get_inventory_stock", {}, READ_TOKEN))

    assert payload["error"] == "invalid_input"


def test_inventory_by_id_uses_detail_endpoint(app_client, monkeypatch) -> None:
    async def _fake(supply_id: int) -> dict:
        assert supply_id == 3
        return dict(PRODUCT_ROW)

    monkeypatch.setattr(backend_client, "get_product", _fake)

    payload = tool_payload(
        call_tool(app_client, "get_inventory_stock", {"supply_id": 3}, READ_TOKEN)
    )

    assert payload["products"][0]["current_stock"] == 120


# --- Backend failure taxonomy reaches the agent unchanged ---


@pytest.mark.parametrize(
    ("kind", "expected_error"),
    [
        ("not_found", "not_found"),
        ("timeout", "timeout"),
        ("unavailable", "unavailable"),
        ("auth", "auth"),
        ("invalid_input", "invalid_input"),
    ],
)
def test_backend_errors_map_to_contract_errors(
    app_client, monkeypatch, kind, expected_error
) -> None:
    async def _boom(ticket_id: int) -> dict:
        raise backend_client.BackendError(kind, "boom")

    monkeypatch.setattr(backend_client, "get_incident", _boom)

    payload = tool_payload(
        call_tool(app_client, "get_incident_status", {"ticket_id": 7}, READ_TOKEN)
    )

    assert payload["ok"] is False
    assert payload["error"] == expected_error
    assert payload["message"]


def test_tool_failures_are_reported_as_contract_payloads_not_protocol_errors(
    app_client, monkeypatch
) -> None:
    """A backend outage must not look like a protocol/auth problem to the client."""

    async def _boom(ticket_id: int) -> dict:
        raise backend_client.BackendError("unavailable", "down")

    monkeypatch.setattr(backend_client, "get_incident", _boom)

    payload = call_tool(app_client, "get_incident_status", {"ticket_id": 7}, READ_TOKEN)

    assert payload["result"].get("isError") is not True
    assert json.loads(payload["result"]["content"][0]["text"])["error"] == "unavailable"
