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

INCIDENT_TOOL_NEEDS_ID_MESSAGE = (
    "Which ticket do you mean? Please include its number "
    "(for example, \"status of ticket 12\") so I can look it up."
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

INVENTORY_TOOL_NEEDS_PRODUCT_MESSAGE = (
    "Which product do you mean? Please include its name or SKU "
    "(for example, \"stock of nitrile gloves\" or \"HCR-PPE-001\")."
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
    """Turn a tool result into a coordinator-facing answer (no invented fields).

    Free-text fields from the external incidents API pass the content-
    isolation guard: instruction-like text inside a ticket title/description
    is data, never a system instruction.
    """
    from data.pipelines import agent_content_guard

    if not result.ok:
        return agent_content_guard.sanitize_tool_text(
            result.message or INCIDENT_TOOL_FALLBACK
        )
    if not result.incidents:
        return INCIDENT_NOT_FOUND_MESSAGE

    return " ".join(describe_incident(item) for item in result.incidents)


# --- Natural-language rendering (deterministic, no LLM, no invented fields) ---

_STATUS_PHRASES = {
    "open": "open",
    "in_progress": "in progress",
    "resolved": "resolved",
    "discarded": "discarded",
}
_ORIGIN_PHRASES = {
    "customer": "reported by a customer",
    "branch": "reported by branch staff",
    "internal": "raised internally",
}
_CATEGORY_PHRASES = {
    "clinical_equipment": "clinical equipment issue",
    "it_system": "IT system issue",
    "billing_error": "billing error",
    "compliance_breach": "compliance breach",
    "patient_experience": "patient experience issue",
    "staff_issue": "staff issue",
    "facility_issue": "facility issue",
    "referral_issue": "referral issue",
    "other": "general issue",
}
_BRANCH_NAMES = {"london_city": "London City", "london_west": "London West"}
_UNIT_PLURALS = {"box": "boxes", "unit": "units", "pack": "packs", "vial": "vials"}


def _humanize_key(value: str) -> str:
    """``billing_error`` -> ``billing error`` (enum keys read as words)."""
    return " ".join(str(value or "").replace("_", " ").split())


def _branch_name(value: str) -> str:
    if value in _BRANCH_NAMES:
        return _BRANCH_NAMES[value]
    return " ".join(word.capitalize() for word in _humanize_key(value).split())


def _human_date(value: str) -> str:
    """ISO timestamp -> ``Jan 20, 2024``; unknown shapes are returned as-is."""
    from datetime import datetime

    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    return f"{parsed:%b} {parsed.day}, {parsed.year}"


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def describe_incident(item: IncidentRecord) -> str:
    """One incident as plain English sentences (content-guarded title)."""
    from data.pipelines import agent_content_guard

    title = agent_content_guard.sanitize_tool_text(item.title).strip()
    status = _STATUS_PHRASES.get(item.status, _humanize_key(item.status))
    head = f"Ticket #{item.id}"
    if title:
        head += f" (\u201c{title}\u201d)"
    sentences = [f"{head} is currently {status}."]
    category = _CATEGORY_PHRASES.get(item.category, _humanize_key(item.category))
    parts: list[str] = []
    if category:
        parts.append(f"It is {_article(category)} {category}")
    origin = _ORIGIN_PHRASES.get(item.origin, "")
    if origin:
        parts.append(origin if parts else f"It was {origin}")
    if item.branch:
        branch = f"at the {_branch_name(item.branch)} branch"
        parts.append(branch if parts else f"It is logged {branch}")
    if parts:
        sentences.append(" ".join(parts) + ".")
    updated = _human_date(item.updated_at)
    if updated:
        sentences.append(f"It was last updated on {updated}.")
    return " ".join(sentences)


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
    """Turn an inventory tool result into a coordinator-facing answer.

    Free-text fields (product name, failure message) pass the content-
    isolation guard — external tool text is data, never instructions.
    """
    from data.pipelines import agent_content_guard

    if not result.ok:
        return agent_content_guard.sanitize_tool_text(
            result.message or INVENTORY_TOOL_FALLBACK
        )
    if not result.products:
        return INVENTORY_NOT_FOUND_MESSAGE

    return " ".join(describe_stock(item) for item in result.products)


def _quantity(count: int, unit: str) -> str:
    unit = (unit or "").strip().lower()
    if not unit:
        return f"{count:,}"
    if count == 1:
        return f"{count:,} {unit}"
    return f"{count:,} {_UNIT_PLURALS.get(unit, unit + 's')}"


def describe_stock(item: InventoryRecord) -> str:
    """One inventory row as a plain English sentence (content-guarded name)."""
    from data.pipelines import agent_content_guard

    name = agent_content_guard.sanitize_tool_text(item.name).strip()
    country = (item.country or "").strip()
    where = f" in the {country}" if country in ("US", "UK") else (
        f" in {country}" if country else ""
    )
    if item.current_stock <= 0:
        return f"{name} (SKU {item.sku}) is out of stock{where}."
    return (
        f"We currently have {_quantity(item.current_stock, item.unit)} of "
        f"{name} (SKU {item.sku}) in stock{where}."
    )
