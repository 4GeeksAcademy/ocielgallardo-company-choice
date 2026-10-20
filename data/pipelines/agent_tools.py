"""Shared tool contracts and answer formatters for the HealthCore agent tools.

Responsibility: the typed models both sides of the MCP boundary already agree
on — ``IncidentToolInput`` / ``IncidentToolOutput`` and
``InventoryToolInput`` / ``InventoryToolOutput`` — plus the deterministic
formatters that turn a tool result into a coordinator-facing answer.

There is **no HTTP business-data access in this module** anymore: live
lookups travel over MCP only (``data/pipelines/mcp_client.py`` for the agent,
``mcps/incidents-inventory-mcp`` for the server). The module is statically
guarded in tests: no HTTP client, no write verbs.

The only HTTP POST in the agent data path is the client-credentials grant in
``data/pipelines/service_token_provider.py`` (env-driven credentials,
auto-renewed — never a pasted user session, see ``docs/rag/agent-graph.md``
§9.1). Failures never invent state: the taxonomy is ``not_found | timeout |
unavailable | invalid_input | auth``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

INCIDENT_TOOL_FALLBACK = (
    "I could not confirm the status of that ticket right now. "
    "Please check the incident manager directly or try again shortly."
)

INCIDENT_NOT_FOUND_MESSAGE = (
    "I could not find that ticket in the incident manager. "
    "Please verify the ticket id and try again."
)

INCIDENT_TOOL_AUTH_MESSAGE = (
    "I could not confirm the status of that ticket because the service "
    "credentials were rejected. Please try again shortly."
)

INVENTORY_TOOL_FALLBACK = (
    "I could not confirm inventory stock right now. "
    "Please check the inventory module directly or try again shortly."
)

INVENTORY_NOT_FOUND_MESSAGE = (
    "I could not find that product in the inventory. "
    "Please verify the SKU or product name and try again."
)

INVENTORY_TOOL_AUTH_MESSAGE = (
    "I could not confirm inventory stock because the service credentials "
    "were rejected. Please try again shortly."
)


class IncidentToolInput(BaseModel):
    """Typed input for the incident lookup tool (read-only)."""

    ticket_id: int | None = Field(
        default=None,
        description="Document id for the incident detail lookup",
        ge=1,
    )
    status: str | None = Field(
        default=None,
        description="Optional exact-match status filter for the incident list",
    )
    origin: str | None = None
    branch: str | None = None
    category: str | None = None


class IncidentRecord(BaseModel):
    """Fields exposed by the incident manager API (detail shape)."""

    id: int
    title: str
    description: str
    category: str
    status: str
    origin: str
    branch: str
    created_at: str = ""
    updated_at: str = ""


class IncidentToolOutput(BaseModel):
    """Typed tool result: success payload or honest failure (never invented state)."""

    ok: bool
    incidents: list[IncidentRecord] = Field(default_factory=list)
    error: (
        Literal["not_found", "timeout", "unavailable", "invalid_input", "auth"]
        | None
    ) = None
    message: str | None = None


def _record_from_api(payload: dict) -> IncidentRecord:
    return IncidentRecord(
        id=int(payload["id"]),
        title=str(payload.get("title", "")),
        description=str(payload.get("description", "")),
        category=str(payload.get("category", "")),
        status=str(payload.get("status", "")),
        origin=str(payload.get("origin", "")),
        branch=str(payload.get("branch", "")),
        created_at=str(payload.get("created_at", "") or ""),
        updated_at=str(payload.get("updated_at", "") or ""),
    )


def format_incident_answer(result: IncidentToolOutput) -> str:
    """Turn a tool result into a coordinator-facing answer (no invented fields)."""
    if not result.ok:
        return result.message or INCIDENT_TOOL_FALLBACK
    if not result.incidents:
        return INCIDENT_NOT_FOUND_MESSAGE

    lines: list[str] = []
    for item in result.incidents:
        lines.append(
            f"Ticket {item.id}: status={item.status}, category={item.category}, "
            f"origin={item.origin}, branch={item.branch}, "
            f"title={item.title!r}, updated_at={item.updated_at}."
        )
    return " ".join(lines)


# --- Inventory stock contracts (single responsibility, same rules) ---


class InventoryToolInput(BaseModel):
    """Typed input for the inventory stock tool (read-only)."""

    sku: str | None = Field(
        default=None,
        description="Exact SKU match (e.g. HCR-PPE-001)",
    )
    name_query: str | None = Field(
        default=None,
        description="Case-insensitive substring match against product name",
    )
    supply_id: int | None = Field(default=None, ge=1)


class InventoryRecord(BaseModel):
    """Fields exposed by the inventory products API."""

    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str
    current_stock: int


class InventoryToolOutput(BaseModel):
    """Typed inventory result: success payload or honest failure."""

    ok: bool
    products: list[InventoryRecord] = Field(default_factory=list)
    error: (
        Literal["not_found", "timeout", "unavailable", "invalid_input", "auth"]
        | None
    ) = None
    message: str | None = None


def _supply_from_api(payload: dict) -> InventoryRecord:
    return InventoryRecord(
        id=int(payload["id"]),
        name=str(payload.get("name", "")),
        sku=str(payload.get("sku", "")),
        category=str(payload.get("category", "")),
        unit=str(payload.get("unit", "")),
        country=str(payload.get("country", "")),
        current_stock=int(payload.get("current_stock", 0)),
    )


def format_inventory_answer(result: InventoryToolOutput) -> str:
    """Turn an inventory tool result into a coordinator-facing answer."""
    if not result.ok:
        return result.message or INVENTORY_TOOL_FALLBACK
    if not result.products:
        return INVENTORY_NOT_FOUND_MESSAGE

    lines: list[str] = []
    for item in result.products:
        lines.append(
            f"{item.name} (SKU {item.sku}): current_stock={item.current_stock} "
            f"{item.unit}, category={item.category}, country={item.country}."
        )
    return " ".join(lines)
