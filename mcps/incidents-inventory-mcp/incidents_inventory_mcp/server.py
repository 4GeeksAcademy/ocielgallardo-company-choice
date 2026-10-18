"""FastMCP server: HealthCore incident and inventory tools.

Exposed tools (scopes are enforced per tool in :mod:`permissions`):

==============================  ========================
Tool                            Required scope
==============================  ========================
``get_incident_status``         ``incidents:read``
``list_incidents``              ``incidents:read``
``create_incident``             ``incidents:write``
``update_incident_status``      ``incidents:write``
``get_inventory_stock``         ``inventory:read``
``update_inventory_stock``      refuses (read-only policy)
==============================  ========================

Design notes:

- **Same contract as the agent tools.** Results are the shared
  :class:`~data.pipelines.agent_tools.IncidentToolOutput` /
  :class:`~data.pipelines.agent_tools.InventoryToolOutput` models, so the agent
  client can validate MCP responses with the models it already trusts and the
  failure taxonomy (``not_found`` / ``timeout`` / ``unavailable`` /
  ``invalid_input`` / ``auth``) does not drift. Return types are annotated, so
  FastMCP advertises ``outputSchema`` and answers with ``structuredContent``
  (``structured_output=True`` on every tool).
- **Stateless HTTP + per-request auth.** Authentication happens at the ASGI
  boundary in :mod:`incidents_inventory_mcp.auth` (MCP Auth); stateless mode
  keeps one request = one verified identity in the auth context variable.
- **No inventory write happens here.** ``update_inventory_stock`` exists so a
  client gets an explicit policy refusal (``inventory_write_denied``) instead
  of an unknown-tool error; it never touches the backend (stock levels stay
  human-only, see ``permissions.INVENTORY_READ_ONLY_MESSAGE``).
- **Audited.** Every tool call logs ``tool= client= result= ms=`` (denials
  included), so scope refusals and read-only refusals are observable.
"""

from __future__ import annotations

import functools
import logging
import os
import time
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

from data.pipelines.agent_tools import (
    INCIDENT_NOT_FOUND_MESSAGE,
    INCIDENT_TOOL_AUTH_MESSAGE,
    INCIDENT_TOOL_FALLBACK,
    INVENTORY_NOT_FOUND_MESSAGE,
    INVENTORY_TOOL_AUTH_MESSAGE,
    INVENTORY_TOOL_FALLBACK,
    IncidentToolOutput,
    InventoryRecord,
    InventoryToolOutput,
    _record_from_api,
    _supply_from_api,
)

from incidents_inventory_mcp import backend_client, permissions

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

SERVER_NAME = "healthcore-incidents-inventory"
STREAMABLE_HTTP_PATH = "/mcp"

ALLOWED_HOSTS_VAR = "MCP_ALLOWED_HOSTS"
ALLOWED_ORIGINS_VAR = "MCP_ALLOWED_ORIGINS"

# DNS-rebinding protection stays on; these host patterns cover loopback, the
# compose service name, Starlette's test client and GitHub Codespaces public
# URLs (*.app.github.dev) used for the MCP Playground validation. Override with
# MCP_ALLOWED_HOSTS when the server is reached through another hostname.
DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1:*",
    "localhost:*",
    "[::1]:*",
    "mcp:*",
    "testserver",
    "testserver:*",
    "*.app.github.dev:*",
    "*.github.dev:*",
]
DEFAULT_ALLOWED_ORIGINS = [
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
    "http://mcp:*",
    "https://*.app.github.dev",
    "https://*.github.dev",
]

INSTRUCTIONS = (
    "HealthCore operational tools for the support agent: look up and open "
    "incidents in the incident manager, move an incident through its lifecycle, "
    "and read inventory stock. Inventory is read-only: stock levels are changed "
    "by human operators only. Every call runs under the scopes of the service "
    "token presented at connect time; calls without the required scope are "
    "rejected and must not be retried with the same token."
)

INCIDENT_ERROR_MESSAGES = {
    "not_found": INCIDENT_NOT_FOUND_MESSAGE,
    "auth": INCIDENT_TOOL_AUTH_MESSAGE,
    "timeout": INCIDENT_TOOL_FALLBACK,
    "unavailable": INCIDENT_TOOL_FALLBACK,
    "invalid_input": INCIDENT_TOOL_FALLBACK,
}

INVENTORY_ERROR_MESSAGES = {
    "not_found": INVENTORY_NOT_FOUND_MESSAGE,
    "auth": INVENTORY_TOOL_AUTH_MESSAGE,
    "timeout": INVENTORY_TOOL_FALLBACK,
    "unavailable": INVENTORY_TOOL_FALLBACK,
    "invalid_input": INVENTORY_TOOL_FALLBACK,
}


def _csv_env(var: str, default: list[str]) -> list[str]:
    """Comma-separated env override, falling back to ``default``."""
    raw = os.getenv(var, "").strip()
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _transport_security() -> TransportSecuritySettings:
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_csv_env(ALLOWED_HOSTS_VAR, DEFAULT_ALLOWED_HOSTS),
        allowed_origins=_csv_env(ALLOWED_ORIGINS_VAR, DEFAULT_ALLOWED_ORIGINS),
    )


def _incident_failure(error: str, message: str) -> IncidentToolOutput:
    return IncidentToolOutput(ok=False, error=error, message=message)


def _inventory_failure(error: str, message: str) -> InventoryToolOutput:
    return InventoryToolOutput(ok=False, error=error, message=message)


def _incident_error(exc: backend_client.BackendError) -> IncidentToolOutput:
    return _incident_failure(exc.kind, INCIDENT_ERROR_MESSAGES[exc.kind])


def _inventory_error(exc: backend_client.BackendError) -> InventoryToolOutput:
    return _inventory_failure(exc.kind, INVENTORY_ERROR_MESSAGES[exc.kind])


def _incident_filter_params(
    status: str | None,
    origin: str | None,
    branch: str | None,
    category: str | None,
) -> dict[str, str]:
    """Only non-empty filters are forwarded (matches the agent tool)."""
    return {
        key: value
        for key, value in {
            "status": status,
            "origin": origin,
            "branch": branch,
            "category": category,
        }.items()
        if value
    }


def _denial_kind(message: str) -> str:
    """Audit result for an expected refusal (scope or read-only policy)."""
    if message.startswith(permissions.INSUFFICIENT_SCOPE_PREFIX):
        return "denied_scope"
    if message.startswith(permissions.INVENTORY_WRITE_DENIED):
        return "denied_policy"
    return "error"


def _audit(tool_name: str):
    """Log every tool execution as ``tool= client= result= ms=``.

    Expected refusals (``ToolError`` from the scope gate or the read-only
    policy) are auditable too; unexpected exceptions are logged and re-raised.
    """

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            started = time.perf_counter()
            client = permissions.current_client_id() or "anonymous"
            try:
                result = await fn(*args, **kwargs)
            except ToolError as exc:
                kind = _denial_kind(str(exc))
                logger.info(
                    "mcp_tool tool=%s client=%s result=%s ms=%.1f",
                    tool_name,
                    client,
                    kind,
                    (time.perf_counter() - started) * 1000,
                )
                raise
            except Exception:
                logger.info(
                    "mcp_tool tool=%s client=%s result=exception ms=%.1f",
                    tool_name,
                    client,
                    (time.perf_counter() - started) * 1000,
                )
                raise
            ok = bool(getattr(result, "ok", True))
            logger.info(
                "mcp_tool tool=%s client=%s result=%s ms=%.1f",
                tool_name,
                client,
                "ok" if ok else "failure",
                (time.perf_counter() - started) * 1000,
            )
            return result

        return wrapper

    return decorator


def build_server() -> FastMCP:
    """Create the FastMCP server (reads ``MCP_*`` settings from the environment).

    No SDK auth here on purpose: OAuth is owned by MCP Auth in
    :mod:`incidents_inventory_mcp.auth`, applied around this app in
    :mod:`incidents_inventory_mcp.app`.
    """
    mcp = FastMCP(
        SERVER_NAME,
        instructions=INSTRUCTIONS,
        streamable_http_path=STREAMABLE_HTTP_PATH,
        stateless_http=True,
        host="0.0.0.0",
        transport_security=_transport_security(),
    )

    @mcp.tool(
        name="get_incident_status",
        description=(
            "Look up one incident by its ticket id and return its current status "
            "and attributes. Requires the incidents:read scope."
        ),
        structured_output=True,
    )
    @_audit("get_incident_status")
    async def get_incident_status(
        ticket_id: Annotated[int, Field(description="Incident id.", ge=1)],
    ) -> IncidentToolOutput:
        permissions.require_scopes("incidents:read")
        try:
            payload = await backend_client.get_incident(ticket_id)
        except backend_client.BackendError as exc:
            return _incident_error(exc)
        return IncidentToolOutput(ok=True, incidents=[_record_from_api(payload)])

    @mcp.tool(
        name="list_incidents",
        description=(
            "List incidents matching at least one exact-match filter. Provide one "
            "or more of status, origin, branch or category; a call with no filter "
            "is rejected. Requires the incidents:read scope."
        ),
        structured_output=True,
    )
    @_audit("list_incidents")
    async def list_incidents(
        status: Annotated[
            str | None,
            Field(description="Incident status: open, in_progress, resolved, discarded."),
        ] = None,
        origin: Annotated[
            str | None,
            Field(description="Incident origin: customer, branch, internal."),
        ] = None,
        branch: Annotated[
            str | None,
            Field(description="Branch key, e.g. austin_north, london_city."),
        ] = None,
        category: Annotated[
            str | None,
            Field(description="Category key, e.g. it_system, billing_error."),
        ] = None,
    ) -> IncidentToolOutput:
        permissions.require_scopes("incidents:read")
        params = _incident_filter_params(status, origin, branch, category)
        if not params:
            return _incident_failure("invalid_input", INCIDENT_TOOL_FALLBACK)
        try:
            rows = await backend_client.get_incidents(params)
        except backend_client.BackendError as exc:
            return _incident_error(exc)
        return IncidentToolOutput(ok=True, incidents=[_record_from_api(row) for row in rows])

    @mcp.tool(
        name="create_incident",
        description=(
            "Open a new incident in the incident manager. category, origin and "
            "branch must be valid HealthCore enum keys, otherwise the manager "
            "rejects the payload. Requires the incidents:write scope."
        ),
        structured_output=True,
    )
    @_audit("create_incident")
    async def create_incident(
        title: Annotated[str, Field(description="Short incident title.", min_length=1)],
        description: Annotated[
            str, Field(description="What happened, in operational terms.", min_length=1)
        ],
        category: Annotated[
            str,
            Field(
                description=(
                    "Category key: clinical_equipment, it_system, billing_error, "
                    "compliance_breach, patient_experience, staff_issue, "
                    "facility_issue, referral_issue, other."
                )
            ),
        ],
        origin: Annotated[
            str, Field(description="Origin key: customer, branch, internal.")
        ],
        branch: Annotated[
            str, Field(description="Branch key, e.g. austin_north, london_city.")
        ],
    ) -> IncidentToolOutput:
        permissions.require_scopes("incidents:write")
        body = {
            "title": title,
            "description": description,
            "category": category,
            "origin": origin,
            "branch": branch,
        }
        try:
            payload = await backend_client.create_incident(body)
        except backend_client.BackendError as exc:
            return _incident_error(exc)
        return IncidentToolOutput(ok=True, incidents=[_record_from_api(payload)])

    @mcp.tool(
        name="update_incident_status",
        description=(
            "Move an incident to a new lifecycle status (the manager validates the "
            "transition). Requires the incidents:write scope."
        ),
        structured_output=True,
    )
    @_audit("update_incident_status")
    async def update_incident_status(
        ticket_id: Annotated[int, Field(description="Incident id.", ge=1)],
        status: Annotated[
            str,
            Field(description="New status: open, in_progress, resolved, discarded."),
        ],
    ) -> IncidentToolOutput:
        permissions.require_scopes("incidents:write")
        try:
            payload = await backend_client.update_incident_status(ticket_id, status)
        except backend_client.BackendError as exc:
            return _incident_error(exc)
        return IncidentToolOutput(ok=True, incidents=[_record_from_api(payload)])

    @mcp.tool(
        name="get_inventory_stock",
        description=(
            "Read current stock for a product by id, exact SKU or name substring. "
            "Read-only: stock levels cannot be changed through this server. "
            "Requires the inventory:read scope."
        ),
        structured_output=True,
    )
    @_audit("get_inventory_stock")
    async def get_inventory_stock(
        supply_id: Annotated[
            int | None, Field(description="Product id.", ge=1)
        ] = None,
        sku: Annotated[
            str | None, Field(description="Exact SKU, e.g. HCR-PPE-001.")
        ] = None,
        name_query: Annotated[
            str | None,
            Field(description="Case-insensitive substring of the product name."),
        ] = None,
    ) -> InventoryToolOutput:
        permissions.require_scopes("inventory:read")
        if supply_id is None and not sku and not name_query:
            return _inventory_failure("invalid_input", INVENTORY_TOOL_FALLBACK)
        try:
            if supply_id is not None:
                payload = await backend_client.get_product(supply_id)
                return InventoryToolOutput(ok=True, products=[_supply_from_api(payload)])

            rows = await backend_client.get_products()
            products: list[InventoryRecord] = [_supply_from_api(row) for row in rows]
            if sku:
                sku_upper = sku.strip().upper()
                products = [item for item in products if item.sku.upper() == sku_upper]
            if name_query:
                needle = name_query.strip().lower()
                products = [item for item in products if needle in item.name.lower()]
        except backend_client.BackendError as exc:
            return _inventory_error(exc)
        if not products:
            return _inventory_failure("not_found", INVENTORY_NOT_FOUND_MESSAGE)
        return InventoryToolOutput(ok=True, products=products)

    @mcp.tool(
        name="update_inventory_stock",
        description=(
            "Refuses any inventory stock change: inventory is read-only on this "
            "server by policy (stock levels are changed by human operators "
            "only). Calling it returns an explicit inventory_write_denied "
            "error; it performs no backend request."
        ),
        structured_output=True,
    )
    @_audit("update_inventory_stock")
    async def update_inventory_stock(
        supply_id: Annotated[int, Field(description="Product id.", ge=1)],
        quantity_change: Annotated[
            int, Field(description="Requested stock delta (never applied).")
        ],
        reason: Annotated[
            str, Field(description="Why the caller wants the change.", min_length=1)
        ],
    ) -> InventoryToolOutput:
        permissions.deny_inventory_write(
            f"supply_id={supply_id} quantity_change={quantity_change} "
            f"reason={reason!r}"
        )
        raise AssertionError("unreachable: deny_inventory_write always raises")

    return mcp


mcp = build_server()

__all__ = ["build_server", "mcp"]
