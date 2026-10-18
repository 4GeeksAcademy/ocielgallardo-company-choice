"""OAuth 2.1 / OIDC discovery endpoints (the API as authorization server).

Serves what MCP Auth (``mcpauth``) fetches when the MCP server starts up:

- ``GET /.well-known/openid-configuration`` (RFC 8414 / OIDC discovery),
- ``GET /.well-known/oauth-authorization-server`` (same document),
- ``GET /.well-known/jwks.json`` — RS256 public keys for service tokens.

This deployment issues tokens **only** through the ``client_credentials``
grant (``POST /auth/token``). ``authorization_endpoint`` is advertised
because AS metadata requires the field; the route answers with an explicit
OAuth error instead of pretending an interactive flow exists.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.app.core import oauth_keys
from services.app.core.security import OAUTH_ISSUER_URL

router = APIRouter(tags=["oauth"])

# Scopes the API can grant (kept in sync with routes that enforce them).
SCOPES_SUPPORTED: tuple[str, ...] = (
    "incidents:read",
    "incidents:write",
    "inventory:read",
)


def authorization_server_metadata() -> dict:
    """RFC 8414 metadata document for this API (issuer is a stable name)."""
    return {
        "issuer": OAUTH_ISSUER_URL,
        "authorization_endpoint": f"{OAUTH_ISSUER_URL}/auth/authorize",
        "token_endpoint": f"{OAUTH_ISSUER_URL}/auth/token",
        "jwks_uri": f"{OAUTH_ISSUER_URL}/.well-known/jwks.json",
        # client-credentials only: no interactive grant is offered here.
        "response_types_supported": [],
        "grant_types_supported": ["client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": list(SCOPES_SUPPORTED),
        "id_token_signing_alg_values_supported": ["RS256"],
        "subject_types_supported": ["public"],
        "service_documentation": f"{OAUTH_ISSUER_URL}/docs",
    }


@router.get("/.well-known/openid-configuration")
@router.get("/.well-known/oauth-authorization-server")
def openid_configuration() -> dict:
    return authorization_server_metadata()


@router.get("/.well-known/jwks.json")
def jwks() -> dict:
    return oauth_keys.get_public_jwks()


@router.get("/auth/authorize")
def authorize_not_supported() -> JSONResponse:
    """Honest stub: interactive grants are out of scope for this deployment."""
    return JSONResponse(
        status_code=501,
        content={
            "error": "unsupported_response_type",
            "error_description": (
                "authorization_code is not enabled on this authorization "
                "server; obtain a token via the client-credentials grant "
                "at POST /auth/token."
            ),
        },
    )


__all__ = ["authorization_server_metadata", "router"]
