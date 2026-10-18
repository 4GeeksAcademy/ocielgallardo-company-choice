"""Fixtures for the MCP server tests.

The MCP package lives in ``mcps/incidents-inventory-mcp`` (outside the repo
package layout), so this conftest puts it on ``sys.path`` and drives the server
through a Starlette ``TestClient``: the full HTTP stack (MCP Auth bearer
middleware, RFC 9728 metadata route, Streamable HTTP endpoint) is exercised
exactly as a remote client reaches it.

Authorization-server reality check: the app fetches
``{MCP_AUTH_ISSUER_URL}/.well-known/openid-configuration`` at build time, so a
tiny stub AS (discovery + JWKS, real HTTP on a fixed port) stands in for the
HealthCore API. Production code runs unmodified; only the issuer URL points at
the stub.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_PACKAGE = _REPO_ROOT / "mcps" / "incidents-inventory-mcp"
for _path in (_REPO_ROOT, _MCP_PACKAGE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from tests.mcps.mcp_helpers import ISSUER_URL, RESOURCE_URL, TEST_JWK  # noqa: E402

_STUB_HOST = "127.0.0.1"
_STUB_PORT = int(ISSUER_URL.rsplit(":", 1)[1])


class _StubAuthServerHandler(BaseHTTPRequestHandler):
    """Discovery + JWKS endpoints of the stub authorization server."""

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path == "/.well-known/openid-configuration":
            self._send_json(
                {
                    "issuer": ISSUER_URL,
                    "authorization_endpoint": f"{ISSUER_URL}/auth/authorize",
                    "token_endpoint": f"{ISSUER_URL}/auth/token",
                    "jwks_uri": f"{ISSUER_URL}/.well-known/jwks.json",
                    "response_types_supported": [],
                    "grant_types_supported": ["client_credentials"],
                    "token_endpoint_auth_methods_supported": [
                        "client_secret_post",
                        "client_secret_basic",
                    ],
                    "subject_types_supported": ["public"],
                    "id_token_signing_alg_values_supported": ["RS256"],
                    "scopes_supported": [
                        "incidents:read",
                        "incidents:write",
                        "inventory:read",
                    ],
                }
            )
        elif self.path == "/.well-known/jwks.json":
            self._send_json({"keys": [TEST_JWK]})
        else:
            self.send_error(404)

    def _send_json(self, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args) -> None:  # keep test output clean
        pass


@pytest.fixture(scope="session", autouse=True)
def _mcp_env() -> None:
    """Environment the MCP server reads (test-only issuer: the stub AS)."""
    os.environ["MCP_RESOURCE_URL"] = RESOURCE_URL
    os.environ["MCP_AUTH_ISSUER_URL"] = ISSUER_URL
    os.environ.setdefault("MCP_BACKEND_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session", autouse=True)
def _stub_auth_server(_mcp_env):
    """Real HTTP stub AS on ``ISSUER_URL``: discovery document + JWKS."""
    server = ThreadingHTTPServer((_STUB_HOST, _STUB_PORT), _StubAuthServerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def anyio_backend() -> str:
    """Pin async tests to asyncio (trio is not a project dependency)."""
    return "asyncio"


@pytest.fixture(scope="session")
def app_client(_mcp_env, _stub_auth_server):
    """Starlette test client over the real ASGI app (lifespan included).

    Session-scoped because the Streamable HTTP session manager can only be
    started once per app instance: one client serves the whole suite, exactly
    like one long-lived process serving many requests. Depends on the stub AS
    because building the app fetches the issuer's metadata.
    """
    from starlette.testclient import TestClient

    from incidents_inventory_mcp.app import app

    with TestClient(app) as client:
        yield client
