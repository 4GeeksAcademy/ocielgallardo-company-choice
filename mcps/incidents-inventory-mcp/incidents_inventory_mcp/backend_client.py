"""Single HTTP choke point between the MCP server and the HealthCore API.

Every backend call goes through :func:`request`, which resolves the target from
the declarative :data:`ENDPOINTS` allowlist. Nothing else in this package uses
``httpx`` for API traffic, so the allowlist is the whole surface: a test asserts
it stays a subset of the reviewed routes and that every inventory endpoint is a
``GET`` (inventory is read-only by design — see ``permissions``).

Auth is the MCP server's *own* service identity (``MCP_BACKEND_CLIENT_ID`` /
``MCP_BACKEND_CLIENT_SECRET``, or ``..._FILE`` for mounted secrets), never the
caller's token: the MCP server must hold ``incidents:write`` to write, and the
API keeps inventory writes human-only.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

import httpx

from data.pipelines.service_token_provider import get_service_token

logger = logging.getLogger(__name__)

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
BACKEND_URL_VAR = "MCP_BACKEND_URL"
CREDENTIAL_PREFIX = "MCP_BACKEND"
BACKEND_TIMEOUT_SECONDS = 5.0

BackendErrorKind = Literal[
    "not_found", "timeout", "unavailable", "invalid_input", "auth"
]

# Declarative endpoint allowlist (endpoint key -> method, path template).
# Inventory entries are GET-only by design: the API itself keeps inventory
# writes human-only, and this server never needs to attempt one.
ENDPOINTS: dict[str, tuple[str, str]] = {
    "incidents_list": ("GET", "/api/incidents"),
    "incident_detail": ("GET", "/api/incidents/{ticket_id}"),
    "incident_create": ("POST", "/api/incidents"),
    "incident_status_update": ("PATCH", "/api/incidents/{ticket_id}/status"),
    "products_list": ("GET", "/inventory/products"),
    "product_detail": ("GET", "/inventory/products/{supply_id}"),
}

READ_ONLY_PREFIXES = ("/inventory/",)


class BackendError(Exception):
    """Backend failure mapped to the agent tool error taxonomy."""

    def __init__(self, kind: BackendErrorKind, message: str = "") -> None:
        super().__init__(message or kind)
        self.kind = kind
        self.message = message


def backend_url() -> str:
    """Base URL of the HealthCore API (env, never hardcoded)."""
    return os.getenv(BACKEND_URL_VAR, DEFAULT_BACKEND_URL).rstrip("/")


def _auth_headers() -> dict[str, str]:
    """Bearer header from the MCP server's auto-renewing service token."""
    token = get_service_token(CREDENTIAL_PREFIX, BACKEND_URL_VAR)
    if not token:
        logger.warning(
            "No service token for prefix %s; backend calls will lack auth",
            CREDENTIAL_PREFIX,
        )
        return {}
    return {"Authorization": f"Bearer {token}"}


def _raise_for_status(response: httpx.Response, endpoint: str) -> None:
    status = response.status_code
    if status in (401, 403):
        logger.warning(
            "Backend rejected MCP service credentials on %s (HTTP %s)",
            endpoint,
            status,
        )
        raise BackendError("auth", "the service credentials were rejected")
    if status == 404:
        raise BackendError("not_found", "the requested resource does not exist")
    if status == 422:
        raise BackendError("invalid_input", "the backend rejected the payload")
    # The incident manager reports domain validation errors as 400 (see
    # ``_validation_http_exception`` in services/app/routers/incidents.py).
    if status == 400:
        raise BackendError("invalid_input", "the backend rejected the payload")
    if status >= 400:
        logger.warning("Backend error on %s (HTTP %s)", endpoint, status)
        raise BackendError("unavailable", f"the backend answered HTTP {status}")


async def request(
    endpoint: str,
    *,
    path_params: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    """Call an allowlisted backend endpoint and return its JSON body.

    Raises :class:`BackendError` for every failure mode (timeout, transport,
    auth, 404, unexpected status) so tools can answer honestly instead of
    inventing data.
    """
    try:
        method, path_template = ENDPOINTS[endpoint]
    except KeyError as exc:
        raise BackendError("unavailable", f"unknown endpoint {endpoint!r}") from exc

    path = path_template.format(**(path_params or {}))
    url = f"{backend_url()}{path}"
    try:
        async with httpx.AsyncClient(timeout=BACKEND_TIMEOUT_SECONDS) as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=_auth_headers(),
            )
    except httpx.TimeoutException as exc:
        logger.warning("Backend %s timed out", endpoint)
        raise BackendError("timeout", "the backend did not answer in time") from exc
    except httpx.HTTPError as exc:
        logger.warning("Backend %s transport failure: %s", endpoint, type(exc).__name__)
        raise BackendError("unavailable", "the backend is unreachable") from exc

    _raise_for_status(response, endpoint)
    try:
        return response.json()
    except ValueError as exc:
        logger.warning("Backend %s answered non-JSON", endpoint)
        raise BackendError("unavailable", "the backend answered non-JSON") from exc


# --- Typed helpers (the only callers of ``request``) ---


async def get_incidents(params: dict[str, Any] | None = None) -> list[dict]:
    """``GET /api/incidents`` with optional exact-match filters."""
    payload = await request("incidents_list", params=params or None)
    return payload if isinstance(payload, list) else []


async def get_incident(ticket_id: int) -> dict:
    """``GET /api/incidents/{id}``."""
    payload = await request("incident_detail", path_params={"ticket_id": ticket_id})
    if not isinstance(payload, dict):
        raise BackendError("unavailable", "the backend answered an unexpected shape")
    return payload


async def create_incident(body: dict) -> dict:
    """``POST /api/incidents`` (requires the service identity to hold ``incidents:write``)."""
    payload = await request("incident_create", json_body=body)
    if not isinstance(payload, dict):
        raise BackendError("unavailable", "the backend answered an unexpected shape")
    return payload


async def update_incident_status(ticket_id: int, status: str) -> dict:
    """``PATCH /api/incidents/{id}/status`` (requires ``incidents:write``)."""
    payload = await request(
        "incident_status_update",
        path_params={"ticket_id": ticket_id},
        json_body={"status": status},
    )
    if not isinstance(payload, dict):
        raise BackendError("unavailable", "the backend answered an unexpected shape")
    return payload


async def get_products() -> list[dict]:
    """``GET /inventory/products`` (read-only by design)."""
    payload = await request("products_list")
    return payload if isinstance(payload, list) else []


async def get_product(supply_id: int) -> dict:
    """``GET /inventory/products/{id}`` (read-only by design)."""
    payload = await request("product_detail", path_params={"supply_id": supply_id})
    if not isinstance(payload, dict):
        raise BackendError("unavailable", "the backend answered an unexpected shape")
    return payload
