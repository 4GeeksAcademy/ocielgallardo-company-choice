"""Helpers for driving the MCP server from tests.

Kept out of ``conftest.py`` so both the fixtures and the test modules import the
same token minting and JSON-RPC plumbing from one place.

Tokens are minted like the API's client-credentials grant: RS256 signed with a
test RSA key whose public half is served by the stub authorization server's
JWKS (see ``tests/mcps/conftest.py``). ``ISSUER_URL`` points at that stub, so
the real mcpauth startup fetch (``fetch_server_config``) runs against it.
"""

from __future__ import annotations

import json
import time
from typing import Any

import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

RESOURCE_URL = "http://localhost:8100/mcp"
# Stub authorization server (discovery + JWKS) started by the conftest fixture.
ISSUER_URL = "http://127.0.0.1:8900"
TEST_KID = "mcp-test-key"
# Only used to emulate an HS256 human-session token (must fail against JWKS).
TEST_HS256_SECRET = "human-session-test-secret-0123456789abcdef"

# Process-wide test RSA key: the JWKS stub serves TEST_JWK, minting uses PRIVATE_PEM.
_RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _private_pem(key: rsa.RSAPrivateKey) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


PRIVATE_PEM = _private_pem(_RSA_KEY)
# Same kid, different key: exercises signature validation, not key lookup.
OTHER_PRIVATE_PEM = _private_pem(OTHER_RSA_KEY)

TEST_JWK: dict[str, Any] = json.loads(
    pyjwt.algorithms.RSAAlgorithm.to_jwk(_RSA_KEY.public_key())
)
TEST_JWK.update({"kid": TEST_KID, "use": "sig", "alg": "RS256"})

JSON_RPC_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "tests", "version": "0"},
    },
}
LIST_TOOLS = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}


def mint_token(
    scopes: list[str] | tuple[str, ...] = ("incidents:read",),
    *,
    subject: str = "svc:mcp-server",
    token_type: str = "service",
    expires_in: int = 900,
    scope_claim: str | None = None,
    audience: str | None = RESOURCE_URL,
    issuer: str | None = ISSUER_URL,
    client_id: str = "mcp-server",
    algorithm: str = "RS256",
    private_pem: str = PRIVATE_PEM,
) -> str:
    """Mint a JWT with the claims the API's client-credentials grant issues."""
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": subject,
        "typ": token_type,
        "scope": scope_claim if scope_claim is not None else " ".join(scopes),
        "iat": now,
        "exp": now + expires_in,
        "iss": issuer,
        "client_id": client_id,
    }
    if audience is not None:
        claims["aud"] = audience
    headers = {"kid": TEST_KID} if algorithm == "RS256" else None
    return str(pyjwt.encode(claims, private_pem, algorithm=algorithm, headers=headers))


def post_json_rpc(client, body: dict, token: str | None = None):
    """POST one JSON-RPC message and return ``(response, parsed_payload)``.

    Streamable HTTP answers either JSON or SSE; both framings are handled so
    tests assert on the JSON-RPC payload, not on the transport encoding.
    """
    headers = dict(JSON_RPC_HEADERS)
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    response = client.post("/mcp", json=body, headers=headers)
    payload: Any = None
    for line in response.text.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[len("data: ") :])
            break
    if payload is None and response.text:
        try:
            payload = json.loads(response.text)
        except ValueError:
            payload = None
    return response, payload


def call_tool(client, name: str, arguments: dict, token: str | None = None):
    """Call one MCP tool; returns the parsed JSON-RPC payload."""
    return post_json_rpc(
        client,
        {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        token,
    )[1]


def tool_error_text(payload: dict) -> str:
    """Text of an error tool result (``isError`` results carry the reason)."""
    result = payload["result"]
    assert result.get("isError") is True, payload
    return "".join(block.get("text", "") for block in result.get("content", []))


def tool_payload(payload: dict) -> dict:
    """JSON payload of a successful tool result (contract-shaped)."""
    result = payload["result"]
    assert result.get("isError") is not True, payload
    text = "".join(block.get("text", "") for block in result.get("content", []))
    return json.loads(text)
