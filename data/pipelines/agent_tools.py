"""Read-only agent tools over live HealthCore operational services.

Responsibility: typed contracts + timed lookups against the existing incident
manager (and later inventory). Tools never create/update/delete. They call the
in-process domain layer (same TinyDB/SQLModel stores as the HTTP APIs), not a
parallel fake dataset. HTTP auth is not required on this path because the tool
runs inside the backend process; the public HTTP routes remain Bearer-protected.

Timeouts are numeric and enforced via ``ThreadPoolExecutor`` so a hung store
cannot block the LangGraph run (Windows-safe; no signals).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Explicit numeric timeout for every external-service tool call (seconds).
INCIDENT_TOOL_TIMEOUT_SECONDS = 5.0

INCIDENT_TOOL_FALLBACK = (
    "I could not confirm the status of that ticket right now. "
    "Please check the incident manager directly or try again shortly."
)

INCIDENT_NOT_FOUND_MESSAGE = (
    "I could not find that ticket in the incident manager. "
    "Please verify the ticket id and try again."
)


class IncidentToolInput(BaseModel):
    """Typed input for the incident lookup tool (read-only)."""

    ticket_id: int | None = Field(
        default=None,
        description="TinyDB document id for GET /api/incidents/{id}",
        ge=1,
    )
    status: str | None = Field(
        default=None,
        description="Optional exact-match filter aligned with GET /api/incidents",
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
    created_at: str
    updated_at: str


class IncidentToolOutput(BaseModel):
    """Typed tool result: success payload or honest failure (never invented state)."""

    ok: bool
    incidents: list[IncidentRecord] = Field(default_factory=list)
    error: (
        Literal["not_found", "timeout", "unavailable", "invalid_input"] | None
    ) = None
    message: str | None = None


def _incident_to_record(incident) -> IncidentRecord:
    return IncidentRecord(
        id=int(incident.id),
        title=str(incident.title),
        description=str(incident.description),
        category=str(
            incident.category.value
            if hasattr(incident.category, "value")
            else incident.category
        ),
        status=str(
            incident.status.value
            if hasattr(incident.status, "value")
            else incident.status
        ),
        origin=str(
            incident.origin.value
            if hasattr(incident.origin, "value")
            else incident.origin
        ),
        branch=str(
            incident.branch.value
            if hasattr(incident.branch, "value")
            else incident.branch
        ),
        created_at=str(incident.created_at),
        updated_at=str(incident.updated_at),
    )


def _fetch_incidents(payload: IncidentToolInput) -> list[IncidentRecord]:
    """Call the real incident manager domain layer (GET semantics only)."""
    from services.app.domain.incident_manager_service import (
        IncidentNotFoundError,
        get_incident,
        list_incidents,
    )

    if payload.ticket_id is not None:
        try:
            incident = get_incident(payload.ticket_id)
        except IncidentNotFoundError:
            return []
        return [_incident_to_record(incident)]

    rows = list_incidents(
        status=payload.status,
        origin=payload.origin,
        branch=payload.branch,
        category=payload.category,
    )
    return [_incident_to_record(row) for row in rows]


def lookup_incident(
    payload: IncidentToolInput,
    *,
    timeout_seconds: float = INCIDENT_TOOL_TIMEOUT_SECONDS,
) -> IncidentToolOutput:
    """Read-only incident lookup with an explicit numeric timeout and fallback.

    - Uses ``get_incident`` / ``list_incidents`` from the existing manager.
    - Never invents ticket state on failure, timeout, or missing id.
    - Timeout default: ``INCIDENT_TOOL_TIMEOUT_SECONDS`` (5.0).
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
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_fetch_incidents, payload)
            incidents = future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        logger.warning(
            "incident tool timed out after %.1fs (ticket_id=%s)",
            timeout_seconds,
            payload.ticket_id,
        )
        return IncidentToolOutput(
            ok=False,
            error="timeout",
            message=INCIDENT_TOOL_FALLBACK,
        )
    except Exception:
        logger.exception(
            "incident tool failed (ticket_id=%s)", payload.ticket_id
        )
        return IncidentToolOutput(
            ok=False,
            error="unavailable",
            message=INCIDENT_TOOL_FALLBACK,
        )

    if payload.ticket_id is not None and not incidents:
        return IncidentToolOutput(
            ok=False,
            error="not_found",
            message=INCIDENT_NOT_FOUND_MESSAGE,
        )

    return IncidentToolOutput(ok=True, incidents=incidents)


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


# --- Inventory stock lookup (optional extra tool; single responsibility) ---

INVENTORY_TOOL_TIMEOUT_SECONDS = 5.0

INVENTORY_TOOL_FALLBACK = (
    "I could not confirm inventory stock right now. "
    "Please check the inventory module directly or try again shortly."
)

INVENTORY_NOT_FOUND_MESSAGE = (
    "I could not find that product in the inventory. "
    "Please verify the SKU or product name and try again."
)


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


def _supply_to_record(supply) -> InventoryRecord:
    return InventoryRecord(
        id=int(supply.id),
        name=str(supply.name),
        sku=str(supply.sku),
        category=str(supply.category),
        unit=str(supply.unit),
        country=str(supply.country),
        current_stock=int(supply.current_stock),
    )


def _fetch_inventory(payload: InventoryToolInput) -> list[InventoryRecord]:
    """Call the real inventory domain layer (GET /inventory/products semantics)."""
    from fastapi import HTTPException
    from sqlmodel import Session

    from services.app.core.database import get_engine
    from services.app.domain import inventory_service

    with Session(get_engine()) as session:
        if payload.supply_id is not None:
            try:
                supply = inventory_service.get_supply(session, payload.supply_id)
            except HTTPException as exc:
                if exc.status_code == 404:
                    return []
                raise
            return [_supply_to_record(supply)]

        products = inventory_service.list_supplies(session)
        if payload.sku:
            sku_upper = payload.sku.strip().upper()
            products = [p for p in products if str(p.sku).upper() == sku_upper]
        if payload.name_query:
            needle = payload.name_query.strip().lower()
            products = [p for p in products if needle in str(p.name).lower()]
        return [_supply_to_record(p) for p in products]


def lookup_inventory(
    payload: InventoryToolInput,
    *,
    timeout_seconds: float = INVENTORY_TOOL_TIMEOUT_SECONDS,
) -> InventoryToolOutput:
    """Read-only stock lookup with explicit numeric timeout and fallback.

    Uses ``list_supplies`` / ``get_supply`` from the existing inventory service.
    Never invents stock levels on failure, timeout, or missing product.
    """
    if payload.supply_id is None and not payload.sku and not payload.name_query:
        return InventoryToolOutput(
            ok=False,
            error="invalid_input",
            message=INVENTORY_TOOL_FALLBACK,
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_fetch_inventory, payload)
            products = future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        logger.warning(
            "inventory tool timed out after %.1fs (sku=%s name=%s)",
            timeout_seconds,
            payload.sku,
            payload.name_query,
        )
        return InventoryToolOutput(
            ok=False,
            error="timeout",
            message=INVENTORY_TOOL_FALLBACK,
        )
    except Exception:
        logger.exception(
            "inventory tool failed (sku=%s name=%s)",
            payload.sku,
            payload.name_query,
        )
        return InventoryToolOutput(
            ok=False,
            error="unavailable",
            message=INVENTORY_TOOL_FALLBACK,
        )

    if not products:
        return InventoryToolOutput(
            ok=False,
            error="not_found",
            message=INVENTORY_NOT_FOUND_MESSAGE,
        )

    return InventoryToolOutput(ok=True, products=products)


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
