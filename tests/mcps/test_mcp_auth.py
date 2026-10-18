"""Authentication and authorization tests for the MCP server.

Covers the OAuth resource-server surface (RFC 9728 protected-resource metadata,
bearer rejection paths, JWT verification via MCP Auth) and the per-tool scope
gate, without a backend: auth decisions must not depend on the API being
reachable. The authorization server is the local stub AS from ``conftest``
(discovery + JWKS over real HTTP), so the production fetch/verify code path
runs unmodified.
"""

from __future__ import annotations

import pytest
from jwt import PyJWK
from mcpauth import AuthInfo
from mcpauth.utils import create_verify_jwt

from tests.mcps.mcp_helpers import (
    INITIALIZE,
    ISSUER_URL,
    LIST_TOOLS,
    OTHER_PRIVATE_PEM,
    RESOURCE_URL,
    TEST_HS256_SECRET,
    TEST_JWK,
    mint_token,
    post_json_rpc,
)

from incidents_inventory_mcp.auth import AUTH_CONTEXT
from incidents_inventory_mcp.permissions import (
    INSUFFICIENT_SCOPE_PREFIX,
    INVENTORY_WRITE_DENIED,
    current_client_id,
    current_scopes,
    deny_inventory_write,
    require_scopes,
)

EXPECTED_SCOPES = {"incidents:read", "incidents:write", "inventory:read"}


def _www_authenticate(response) -> str:
    return response.headers.get("www-authenticate", "")


# --- Protected-resource metadata (client discovery) ---


def test_health_is_public_and_does_not_leak_secrets(app_client) -> None:
    response = app_client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["resource"] == RESOURCE_URL
    assert "secret" not in response.text.lower()


def test_protected_resource_metadata_points_at_the_stub_as(app_client) -> None:
    response = app_client.get("/.well-known/oauth-protected-resource/mcp")

    assert response.status_code == 200
    body = response.json()
    assert body["resource"] == RESOURCE_URL
    assert body["bearer_methods_supported"] == ["header"]
    # The HealthCore API (stub AS in tests) mints the RS256 service tokens.
    assert body["authorization_servers"] == [ISSUER_URL]
    assert set(body["scopes_supported"]) == EXPECTED_SCOPES


def test_jwks_uri_env_override_redirects_the_verification_source(monkeypatch) -> None:
    """``MCP_AUTH_JWKS_URI`` replaces the discovery document's ``jwks_uri``.

    Compose needs this: tokens keep ``iss`` = the public issuer, but the JWKS
    document is only reachable on the compose network.
    """
    from incidents_inventory_mcp.auth import JWKS_URI_VAR, load_auth_server_config

    advertised = load_auth_server_config().metadata.jwks_uri
    assert advertised == f"{ISSUER_URL}/.well-known/jwks.json"

    override = "http://backend:8000/.well-known/jwks.json"
    monkeypatch.setenv(JWKS_URI_VAR, override)
    assert load_auth_server_config().metadata.jwks_uri == override

    # Blank values fall back to the advertised URL (developer convenience).
    monkeypatch.setenv(JWKS_URI_VAR, "   ")
    assert load_auth_server_config().metadata.jwks_uri == advertised


# --- Bearer rejection paths ---


def test_request_without_token_is_401_with_metadata_pointer(app_client) -> None:
    response = app_client.post("/mcp", json=INITIALIZE, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })

    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "missing_auth_header"
    header = _www_authenticate(response)
    assert 'error="missing_auth_header"' in header
    assert "resource_metadata=" in header
    assert "/.well-known/oauth-protected-resource/mcp" in header


@pytest.mark.parametrize(
    ("token_factory", "expected_error"),
    [
        pytest.param(lambda: mint_token(expires_in=-3600), "invalid_token", id="expired"),
        pytest.param(lambda: "not-a-jwt", "invalid_token", id="garbage"),
        pytest.param(
            lambda: mint_token(private_pem=OTHER_PRIVATE_PEM),
            "invalid_token",
            id="wrong-signature",
        ),
        pytest.param(
            lambda: mint_token(
                token_type="access",
                subject="user-1",
                algorithm="HS256",
                private_pem=TEST_HS256_SECRET,
            ),
            "invalid_token",
            id="human-session-hs256",
        ),
        pytest.param(
            lambda: mint_token(issuer="https://evil.example"),
            "invalid_issuer",
            id="wrong-issuer",
        ),
        pytest.param(
            lambda: mint_token(audience="https://other-resource.example/mcp"),
            "invalid_audience",
            id="wrong-audience",
        ),
    ],
)
def test_invalid_tokens_are_401_with_distinct_codes(
    app_client, token_factory, expected_error
) -> None:
    response, payload = post_json_rpc(app_client, INITIALIZE, token_factory())

    assert response.status_code == 401, response.text
    assert payload["error"] == expected_error
    assert "error_description" in payload
    assert expected_error in _www_authenticate(response)
    assert "resource_metadata=" in _www_authenticate(response)


def test_valid_service_token_reaches_the_protocol(app_client) -> None:
    response, payload = post_json_rpc(
        app_client, INITIALIZE, mint_token(["incidents:read"])
    )

    assert response.status_code == 200, response.text
    assert payload["result"]["protocolVersion"]
    assert payload["result"]["serverInfo"]["name"] == "healthcore-incidents-inventory"


def test_tools_list_requires_a_token(app_client) -> None:
    response, _ = post_json_rpc(app_client, LIST_TOOLS, None)
    assert response.status_code == 401


# --- Token verification unit level (no HTTP, mcpauth primitives) ---


def test_minted_token_verifies_with_mcpauth_primitives() -> None:
    verify = create_verify_jwt(PyJWK(TEST_JWK, algorithm="RS256"))
    info = verify(mint_token(["incidents:read", "inventory:read"]))

    assert info.client_id == "mcp-server"
    assert info.subject == "svc:mcp-server"
    assert info.issuer == ISSUER_URL
    assert info.audience == RESOURCE_URL
    assert info.scopes == ["incidents:read", "inventory:read"]


def test_token_without_scopes_verifies_but_is_denied_per_tool() -> None:
    """Authentication (token valid) and authorization (scopes) are separate gates."""
    verify = create_verify_jwt(PyJWK(TEST_JWK, algorithm="RS256"))
    info = verify(mint_token(scope_claim=""))

    assert info.scopes == []
    token = AUTH_CONTEXT.set(info)
    try:
        assert current_scopes() == frozenset()
        with pytest.raises(Exception) as excinfo:
            require_scopes("incidents:read")
        assert INSUFFICIENT_SCOPE_PREFIX in str(excinfo.value)
    finally:
        AUTH_CONTEXT.reset(token)


# --- Per-tool scope gate (verified AuthInfo in context) ---


def _with_scopes(scopes: list[str]):
    info = AuthInfo(
        token="t",
        issuer=ISSUER_URL,
        client_id="mcp-server",
        scopes=list(scopes),
        subject="svc:mcp-server",
        claims={},
    )
    return AUTH_CONTEXT.set(info)


def test_scope_gate_fails_closed_without_identity() -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    assert AUTH_CONTEXT.get() is None
    assert current_scopes() == frozenset()
    assert current_client_id() is None
    with pytest.raises(ToolError) as excinfo:
        require_scopes("incidents:read")
    assert INSUFFICIENT_SCOPE_PREFIX in str(excinfo.value)
    assert AUTH_CONTEXT.get() is None


def test_scope_gate_denies_missing_scope_and_allows_granted_ones() -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    ctx = _with_scopes(["incidents:read"])
    try:
        assert current_client_id() == "mcp-server"
        with pytest.raises(ToolError) as excinfo:
            require_scopes("incidents:write")
        message = str(excinfo.value)
        assert "incidents:write" in message
        assert "operation requires incidents:write" in message
        assert require_scopes("incidents:read") is None
    finally:
        AUTH_CONTEXT.reset(ctx)


def test_inventory_write_guard_is_explicit() -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    with pytest.raises(ToolError) as excinfo:
        deny_inventory_write("restock")

    message = str(excinfo.value)
    assert INVENTORY_WRITE_DENIED in message
    assert "human operator" in message
    assert "restock" in message
