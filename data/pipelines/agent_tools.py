"""Read-only agent tools over live HealthCore operational APIs (HTTP).

Responsibility: typed contracts + timed GET lookups against the existing
incident manager (``GET /api/incidents`` / ``GET /api/incidents/{id}``) and
inventory (``GET /inventory/products`` / ``GET /inventory/products/{id}``).
Tools never create/update/delete; only HTTP GET is used (statically guarded).

Transport: ``httpx`` against ``AGENT_TOOL_API_URL`` (default
``http://127.0.0.1:8000``) with Bearer ``AGENT_TOOL_API_TOKEN`` read from
environment/config — never hardcoded. Timeouts are explicit and numeric
(5.0 s); failures map to honest fallbacks, never invented state.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Explicit numeric timeouts for external-service tool calls (seconds).
INCIDENT_TOOL_TIMEOUT_SECONDS = 5.0
INVENTORY_TOOL_TIMEOUT_SECONDS = 5.0

INCIDENT_TOOL_FALLBACK = (
    "I could not confirm the status of that ticket right now. "
    "Please check the incident manager directly or try again shortly."
)

INCIDENT_NOT_FOUND_MESSAGE = (
    "I could not find that ticket in the incident manager. "
    "Please verify the ticket id and try again."
)

INVENTORY_TOOL_FALLBACK = (
    "I could not confirm inventory stock right now. "
    "Please check the inventory module directly or try again shortly."
)

INVENTORY_NOT_FOUND_MESSAGE = (
    "I could not find that product in the inventory. "
    "Please verify the SKU or product name and try again."
)


def api_base_url() -> str:
    """Base URL of the HealthCore API the tools call (env, never hardcoded)."""
    return os.getenv("AGENT_TOOL_API_URL", "http://127.0.0.1:8000").rstrip("/")


def _auth_headers() -> dict[str, str]:
    token = os.getenv("AGENT_TOOL_API_TOKEN", "").strip()
    if not token:
        logger.warning(
            "AGENT_TOOL_API_TOKEN is not set; API tool calls will lack auth"
        )
        return {}
    return {"Authorization": f"Bearer {token}"}


def _http_get(
    path: str,
    *,
    params: dict | None = None,
    timeout_seconds: float,
) -> httpx.Response:
    """Single HTTP GET entry point (mocked in tests; never POST/PATCH/DELETE)."""
    return httpx.get(
        f"{api_base_url()}{path}",
        params=params,
        headers=_auth_headers(),
        timeout=timeout_seconds,
    )


class IncidentToolInput(BaseModel):
    """Typed input for the incident lookup tool (read-only)."""

    ticket_id: int | None = Field(
        default=None,
        description="Document id for GET /api/incidents/{id}",
        ge=1,
    )
    status: str | None = Field(
        default=None,
        description="Optional exact-match filter for GET /api/incidents",
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
        Literal["not_found", "timeout", "unavailable", "invalid_input"] | None
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


def lookup_incident(
    payload: IncidentToolInput,
    *,
    timeout_seconds: float = INCIDENT_TOOL_TIMEOUT_SECONDS,
) -> IncidentToolOutput:
    """Read-only incident lookup via the real incidents API (GET only).

    - ``GET /api/incidents/{ticket_id}`` for id lookups (404 → not_found).
    - ``GET /api/incidents`` with filters otherwise.
    - Timeout/unreachable/auth errors → honest fallback (never invented state).
    """
    if payload.ticket_id is None and not any(
        (payload.status, payload.origin, payload.branch, payload.category)
    ):
        return IncidentToolOutput(
            ok=False,
            error="invalid_input",
            message=INCIDENT_TOOL_FALLBACK,
        )

    try:
        if payload.ticket_id is not None:
            response = _http_get(
                f"/api/incidents/{payload.ticket_id}",
                timeout_seconds=timeout_seconds,
            )
            if response.status_code == 404:
                return IncidentToolOutput(
                    ok=False,
                    error="not_found",
                    message=INCIDENT_NOT_FOUND_MESSAGE,
                )
            response.raise_for_status()
            return IncidentToolOutput(
                ok=True, incidents=[_record_from_api(response.json())]
            )

        params = {
            key: value
            for key, value in {
                "status": payload.status,
                "origin": payload.origin,
                "branch": payload.branch,
                "category": payload.category,
            }.items()
            if value
        }
        response = _http_get(
            "/api/incidents", params=params, timeout_seconds=timeout_seconds
        )
        response.raise_for_status()
        rows = response.json()
        return IncidentToolOutput(
            ok=True,
            incidents=[_record_from_api(item) for item in rows]
            if isinstance(rows, list)
            else [],
        )
    except httpx.TimeoutException:
        logger.warning(
            "incident tool timed out after %.1fs (ticket_id=%s)",
            timeout_seconds,
            payload.ticket_id,
        )
        return IncidentToolOutput(
            ok=False, error="timeout", message=INCIDENT_TOOL_FALLBACK
        )
    except Exception:
        logger.exception("incident tool failed (ticket_id=%s)", payload.ticket_id)
        return IncidentToolOutput(
            ok=False, error="unavailable", message=INCIDENT_TOOL_FALLBACK
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


# --- Inventory stock lookup (single responsibility, same rules) ---


class InventoryToolInput(BaseModel):
    """Typed input for the inventory stock tool (read-only GET)."""

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
    """Fields exposed by GET /inventory/products."""

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
        Literal["not_found", "timeout", "unavailable", "invalid_input"] | None
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


def lookup_inventory(
    payload: InventoryToolInput,
    *,
    timeout_seconds: float = INVENTORY_TOOL_TIMEOUT_SECONDS,
) -> InventoryToolOutput:
    """Read-only stock lookup via the real inventory API (GET only).

    - ``GET /inventory/products/{supply_id}`` for id lookups (404 → not_found).
    - ``GET /inventory/products`` (client-side SKU/name filter) otherwise.
    - Never invents stock levels on failure, timeout, or missing product.
    """
    if payload.supply_id is None and not payload.sku and not payload.name_query:
        return InventoryToolOutput(
            ok=False,
            error="invalid_input",
            message=INVENTORY_TOOL_FALLBACK,
        )

    try:
        if payload.supply_id is not None:
            response = _http_get(
                f"/inventory/products/{payload.supply_id}",
                timeout_seconds=timeout_seconds,
            )
            if response.status_code == 404:
                return InventoryToolOutput(
                    ok=False,
                    error="not_found",
                    message=INVENTORY_NOT_FOUND_MESSAGE,
                )
            response.raise_for_status()
            return InventoryToolOutput(
                ok=True, products=[_supply_from_api(response.json())]
            )

        response = _http_get(
            "/inventory/products", timeout_seconds=timeout_seconds
        )
        response.raise_for_status()
        rows = response.json()
        products = (
            [_supply_from_api(item) for item in rows]
            if isinstance(rows, list)
            else []
        )
        if payload.sku:
            sku_upper = payload.sku.strip().upper()
            products = [p for p in products if p.sku.upper() == sku_upper]
        if payload.name_query:
            needle = payload.name_query.strip().lower()
            products = [p for p in products if needle in p.name.lower()]
        if not products:
            return InventoryToolOutput(
                ok=False,
                error="not_found",
                message=INVENTORY_NOT_FOUND_MESSAGE,
            )
        return InventoryToolOutput(ok=True, products=products)
    except httpx.TimeoutException:
        logger.warning(
            "inventory tool timed out after %.1fs (sku=%s name=%s)",
            timeout_seconds,
            payload.sku,
            payload.name_query,
        )
        return InventoryToolOutput(
            ok=False, error="timeout", message=INVENTORY_TOOL_FALLBACK
        )
    except Exception:
        logger.exception(
            "inventory tool failed (sku=%s name=%s)",
            payload.sku,
            payload.name_query,
        )
        return InventoryToolOutput(
            ok=False, error="unavailable", message=INVENTORY_TOOL_FALLBACK
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
