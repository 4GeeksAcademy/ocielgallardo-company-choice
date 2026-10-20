"""MCP client used by the agent graph to reach the incidents + inventory server.

MCP is the **only** transport: the graph nodes call this module and there is no
direct HTTP fallback anymore (migración hito 25: un único camino). The graph
nodes are synchronous; the MCP client is async. This module owns the single
bridge between both worlds (a dedicated event-loop thread) so no other module
has to deal with it.

Return contract (never ``None``): every call answers with the shared
``agent_tools`` output models, so the node always has a contract payload:

- success → ``ok: true`` with the data the MCP tool returned;
- MCP disabled (``MCP_SERVER_URL`` unset), no token, unreachable, unauthorized,
  or answering something that is not a valid contract payload → honest
  ``unavailable`` failure;
- a scope denial from the server (``insufficient_scope``) → explicit ``auth``
  failure;
- a call with no usable arguments → ``invalid_input`` (no network attempt).

The token minted per call carries ``aud = MCP_RESOURCE_URL`` (RFC 8707), which
the MCP resource server requires.

Results are validated with the shared ``agent_tools`` output models, so an MCP
answer is held to exactly the same contract the agent already trusts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from data.pipelines.agent_tools import (
    INCIDENT_TOOL_AUTH_MESSAGE,
    INCIDENT_TOOL_FALLBACK,
    INVENTORY_TOOL_AUTH_MESSAGE,
    INVENTORY_TOOL_FALLBACK,
    IncidentToolInput,
    IncidentToolOutput,
    InventoryToolInput,
    InventoryToolOutput,
)
from data.pipelines.service_token_provider import get_service_token

logger = logging.getLogger(__name__)

SERVER_URL_VAR = "MCP_SERVER_URL"
RESOURCE_URL_VAR = "MCP_RESOURCE_URL"
DEFAULT_RESOURCE_URL = "http://localhost:8100/mcp"
SERVER_NAME = "healthcore"
MCP_TOOL_TIMEOUT_SECONDS = 10.0
TOOL_GET_INCIDENT_STATUS = "get_incident_status"
TOOL_LIST_INCIDENTS = "list_incidents"
TOOL_GET_INVENTORY_STOCK = "get_inventory_stock"

_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def server_url() -> str:
    """MCP Streamable HTTP endpoint (empty string means MCP is not configured)."""
    return os.getenv(SERVER_URL_VAR, "").strip()


def resource_url() -> str:
    """MCP resource identifier; the audience (``aud``) minted into the token."""
    return os.getenv(RESOURCE_URL_VAR, DEFAULT_RESOURCE_URL).rstrip("/")


def is_enabled() -> bool:
    """True when the MCP transport is configured for this process."""
    return bool(server_url())


def tool_timeout_seconds() -> float:
    raw = os.getenv("MCP_TOOL_TIMEOUT_SECONDS", "")
    try:
        value = float(raw)
    except ValueError:
        return MCP_TOOL_TIMEOUT_SECONDS
    return value if value > 0 else MCP_TOOL_TIMEOUT_SECONDS


def _connection() -> dict[str, Any] | None:
    """MCP connection config with the agent's freshly minted service token.

    The token is requested with ``audience=<MCP_RESOURCE_URL>`` so it passes
    the resource server's RFC 8707 ``aud`` check.
    """
    token = get_service_token(audience=resource_url())
    if not token:
        logger.warning("MCP transport unavailable: no agent service token")
        return None
    return {
        "transport": "streamable_http",
        "url": server_url(),
        "headers": {"Authorization": f"Bearer {token}"},
        "timeout": tool_timeout_seconds(),
    }


def _get_loop() -> asyncio.AbstractEventLoop:
    """Dedicated event loop thread shared by every MCP call in this process."""
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            loop = asyncio.new_event_loop()
            threading.Thread(
                target=loop.run_forever,
                name="mcp-client-loop",
                daemon=True,
            ).start()
            _loop = loop
        return _loop


def _run(coro, timeout_seconds: float):
    """Run ``coro`` from synchronous code, or fail loudly in async contexts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run_coroutine_threadsafe(coro, _get_loop()).result(
            timeout_seconds
        )
    coro.close()
    raise RuntimeError(
        "mcp_client is synchronous-only; call it from the graph nodes, not from "
        "inside a running event loop"
    )


def _extract_text(result: Any) -> str | None:
    """Text payload of an MCP tool result (adapters return content blocks)."""
    if isinstance(result, str):
        return result
    if isinstance(result, tuple) and result:
        return _extract_text(result[0])
    content = getattr(result, "content", result)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block.get("text")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "\n".join(part for part in parts if part)
        return text or None
    return None


async def _call_tool(tool_name: str, arguments: dict[str, Any]) -> str | None:
    """Call one MCP tool over a fresh session and return its text payload."""
    connection = _connection()
    if connection is None:
        return None
    client = MultiServerMCPClient(
        {SERVER_NAME: connection},
        handle_tool_errors=False,
    )
    tools = await client.get_tools()
    tool = next((item for item in tools if item.name == tool_name), None)
    if tool is None:
        logger.warning("MCP server exposes no %s tool", tool_name)
        return None
    return _extract_text(await tool.ainvoke(arguments))


def _parse_incident(text: str | None) -> IncidentToolOutput | None:
    if not text:
        return None
    try:
        return IncidentToolOutput.model_validate(json.loads(text))
    except (ValueError, TypeError) as exc:
        logger.warning("MCP incident payload not usable: %s", type(exc).__name__)
        return None


def _parse_inventory(text: str | None) -> InventoryToolOutput | None:
    if not text:
        return None
    try:
        return InventoryToolOutput.model_validate(json.loads(text))
    except (ValueError, TypeError) as exc:
        logger.warning("MCP inventory payload not usable: %s", type(exc).__name__)
        return None


def _log_unavailable(kind: str, detail: str) -> None:
    logger.warning("MCP %s unavailable: %s", kind, detail)


def lookup_incident_via_mcp(
    payload: IncidentToolInput,
    *,
    timeout_seconds: float | None = None,
) -> IncidentToolOutput:
    """Incident lookup over MCP; never ``None``.

    Transport/config/parse failures become an honest ``unavailable`` contract
    failure, scope denials become ``auth``, and missing arguments become
    ``invalid_input`` without touching the network.
    """
    if payload.ticket_id is not None:
        tool_name = TOOL_GET_INCIDENT_STATUS
        arguments: dict[str, Any] = {"ticket_id": payload.ticket_id}
    else:
        filters = {
            key: value
            for key, value in {
                "status": payload.status,
                "origin": payload.origin,
                "branch": payload.branch,
                "category": payload.category,
            }.items()
            if value
        }
        if not filters:
            return IncidentToolOutput(
                ok=False, error="invalid_input", message=INCIDENT_TOOL_FALLBACK
            )
        tool_name = TOOL_LIST_INCIDENTS
        arguments = filters

    if not server_url():
        _log_unavailable(tool_name, "MCP_SERVER_URL not configured")
        return IncidentToolOutput(
            ok=False, error="unavailable", message=INCIDENT_TOOL_FALLBACK
        )

    timeout = timeout_seconds or tool_timeout_seconds()
    try:
        text = _run(_call_tool(tool_name, arguments), timeout)
    except Exception as exc:
        if "insufficient_scope" in str(exc):
            _log_unavailable(tool_name, "scope denial")
            return IncidentToolOutput(
                ok=False, error="auth", message=INCIDENT_TOOL_AUTH_MESSAGE
            )
        _log_unavailable(tool_name, f"{type(exc).__name__}: {exc}")
        return IncidentToolOutput(
            ok=False, error="unavailable", message=INCIDENT_TOOL_FALLBACK
        )
    result = _parse_incident(text)
    if result is None:
        _log_unavailable(tool_name, "no usable contract payload")
        return IncidentToolOutput(
            ok=False, error="unavailable", message=INCIDENT_TOOL_FALLBACK
        )
    return result


def lookup_inventory_via_mcp(
    payload: InventoryToolInput,
    *,
    timeout_seconds: float | None = None,
) -> InventoryToolOutput:
    """Inventory lookup over MCP; never ``None`` (same contract as incidents)."""
    arguments = {
        key: value
        for key, value in {
            "supply_id": payload.supply_id,
            "sku": payload.sku,
            "name_query": payload.name_query,
        }.items()
        if value
    }
    if not arguments:
        return InventoryToolOutput(
            ok=False, error="invalid_input", message=INVENTORY_TOOL_FALLBACK
        )

    tool_name = TOOL_GET_INVENTORY_STOCK
    if not server_url():
        _log_unavailable(tool_name, "MCP_SERVER_URL not configured")
        return InventoryToolOutput(
            ok=False, error="unavailable", message=INVENTORY_TOOL_FALLBACK
        )

    timeout = timeout_seconds or tool_timeout_seconds()
    try:
        text = _run(_call_tool(tool_name, arguments), timeout)
    except Exception as exc:
        if "insufficient_scope" in str(exc):
            _log_unavailable(tool_name, "scope denial")
            return InventoryToolOutput(
                ok=False, error="auth", message=INVENTORY_TOOL_AUTH_MESSAGE
            )
        _log_unavailable(tool_name, f"{type(exc).__name__}: {exc}")
        return InventoryToolOutput(
            ok=False, error="unavailable", message=INVENTORY_TOOL_FALLBACK
        )
    result = _parse_inventory(text)
    if result is None:
        _log_unavailable(tool_name, "no usable contract payload")
        return InventoryToolOutput(
            ok=False, error="unavailable", message=INVENTORY_TOOL_FALLBACK
        )
    return result
