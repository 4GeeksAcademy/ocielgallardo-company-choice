"""Per-tool scope enforcement for the MCP server.

MCP Auth authenticates every MCP request (401 without a valid RS256 token from
the HealthCore issuer) and stores the verified identity in a context variable.
Authorization is finer than that: each tool declares the scopes it needs, and a
token without them gets an explicit denial instead of a tool result.

Two invariants matter here:

- **Fail closed.** No verified identity in context (transport misconfiguration,
  unexpected execution context) means denial, never implicit access.
- **Honest errors.** The denial names the missing scopes and the operation, so
  a client knows it must re-authorize with a broader grant instead of guessing.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp.exceptions import ToolError

from incidents_inventory_mcp.auth import AUTH_CONTEXT

logger = logging.getLogger(__name__)

INSUFFICIENT_SCOPE_PREFIX = "insufficient_scope"
# Structured marker for inventory write attempts (read-only by design).
INVENTORY_WRITE_DENIED = "inventory_write_denied"

INVENTORY_READ_ONLY_MESSAGE = (
    "inventory is read-only on this server: no inventory write is performed, "
    "every inventory backend call is a GET, and the API rejects service "
    "principals on inventory writes. Ask a human operator to change stock "
    "levels."
)


def current_scopes() -> frozenset[str]:
    """Scopes of the token MCP Auth verified for the current MCP request."""
    info = AUTH_CONTEXT.get()
    if info is None:
        return frozenset()
    return frozenset(info.scopes or [])


def current_client_id() -> str | None:
    """Service client id of the current request, when authenticated."""
    info = AUTH_CONTEXT.get()
    return info.client_id if info else None


def require_scopes(*required: str) -> None:
    """Raise ``ToolError`` unless the verified token holds every required scope.

    Absent identity (worst case) and missing scopes both fail closed with the
    same explicit message; a successful call returns ``None``.
    """
    granted = current_scopes()
    missing = [scope for scope in required if scope not in granted]
    if not missing:
        return
    logger.warning(
        "Scope denial for client=%s: missing=%s granted=%s",
        current_client_id(),
        ",".join(missing),
        ",".join(sorted(granted)) or "-",
    )
    raise ToolError(
        f"{INSUFFICIENT_SCOPE_PREFIX}: missing {' '.join(missing)} "
        f"(operation requires {' '.join(required)})"
    )


def deny_inventory_write(operation: str) -> None:
    """Defensive guard: MCP inventory is read-only by design.

    Wired to the ``update_inventory_stock`` tool, which exists so a client gets
    this declared, testable refusal (``inventory_write_denied``) instead of an
    unknown-tool error. The guard never performs a backend request.
    """
    raise ToolError(f"{INVENTORY_WRITE_DENIED}: {operation}. {INVENTORY_READ_ONLY_MESSAGE}")
