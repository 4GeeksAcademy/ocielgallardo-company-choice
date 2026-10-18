"""ASGI entry point: MCP Auth in front of the FastMCP Streamable HTTP endpoint.

Stack (outer to inner), built with MCP Auth instead of the SDK's integrated
OAuth helpers:

1. ``mcp_auth.resource_metadata_router()`` — RFC 9728 protected-resource
   metadata at ``/.well-known/oauth-protected-resource/mcp`` (client discovery).
2. ``/health`` — unauthenticated liveness probe for the orchestrator.
3. ``Mount("/")`` around the FastMCP Streamable HTTP app with MCP Auth's
   bearer middleware: RS256 JWT verification against the issuer JWKS, ``iss``
   and ``aud`` checks, 401/403 with distinct OAuth error codes.

The Starlette lifespan runs the MCP session manager (a mounted sub-app does
not get its own lifespan executed by Starlette).

Run locally::

    uv run uvicorn incidents_inventory_mcp.app:app \
        --app-dir mcps/incidents-inventory-mcp --port 8100
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from incidents_inventory_mcp.auth import (
    RESOURCE_URL_VAR,
    DEFAULT_RESOURCE_URL,
    bearer_middleware,
    build_mcp_auth,
)
from incidents_inventory_mcp.server import mcp

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)

HEALTH_PATH = "/health"


@asynccontextmanager
async def lifespan(_app: Starlette):
    # One session manager per process; stateless mode = one request, one
    # MCP Auth context (no cross-request auth state).
    async with mcp.session_manager.run():
        yield


async def health(_request: Request) -> JSONResponse:
    """Liveness probe: process up and resource metadata configured."""
    return JSONResponse(
        {
            "status": "ok",
            "service": "healthcore-incidents-inventory-mcp",
            "resource": os.getenv(RESOURCE_URL_VAR, DEFAULT_RESOURCE_URL),
        }
    )


def create_app() -> Starlette:
    """Build the ASGI app.

    Fetches the authorization-server metadata (``fetch_server_config``) from
    ``MCP_AUTH_ISSUER_URL``, so the API must be reachable at build time.
    """
    mcp_auth = build_mcp_auth()
    bearer = bearer_middleware(mcp_auth)
    return Starlette(
        routes=[
            *mcp_auth.resource_metadata_router().routes,
            Route(HEALTH_PATH, health, methods=["GET"]),
            Mount("/", app=mcp.streamable_http_app(), middleware=[Middleware(bearer)]),
        ],
        lifespan=lifespan,
    )


app = create_app()

__all__ = ["app", "create_app"]
