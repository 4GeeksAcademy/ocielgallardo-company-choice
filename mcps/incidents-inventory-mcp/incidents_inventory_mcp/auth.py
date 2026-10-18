"""OAuth 2.1 resource-server wiring via MCP Auth (``mcpauth``).

The MCP server is an RFC 9728 protected resource whose authorization server is
the HealthCore API. MCP Auth owns the whole transport auth surface:

- ``resource_metadata_router()`` serves
  ``/.well-known/oauth-protected-resource/mcp`` (PRM discovery),
- ``bearer_auth_middleware("jwt", ...)`` verifies bearer JWTs against the
  issuer's JWKS (``fetch_server_config`` once at startup) and enforces
  ``iss``/``aud``, returning distinct 401/403 OAuth error codes,
- the verified identity lands in :data:`AUTH_CONTEXT` (``AuthInfo``), which
  :mod:`permissions` reads for per-tool scope checks.

This replaces the SDK's integrated auth (``token_verifier``/``AuthSettings``):
there is no shared symmetric secret here and no HS256. Only RS256 tokens
minted by the API's client-credentials grant can validate against the API's
JWKS.

Environment:

- ``MCP_AUTH_ISSUER_URL`` — issuer whose discovery document is fetched at
  startup (default ``http://localhost:8000``).
- ``MCP_RESOURCE_URL`` — this resource's identifier and the expected token
  ``aud`` (default ``http://localhost:8100/mcp``).
- ``MCP_AUTH_JWKS_URI`` — optional override for the authorization server's
  ``jwks_uri``. Discovery can announce a JWKS URL that is only reachable from
  inside the compose network (for example ``http://backend:8000/...``) while
  the token ``iss`` must stay the public issuer, so only the JWKS fetch is
  redirected.

:func:`load_auth_server_config` is the module's single network call (sync
``requests`` through mcpauth) and the only seam tests replace by pointing
``MCP_AUTH_ISSUER_URL`` at a local stub authorization server.
"""

from __future__ import annotations

import os
from contextvars import ContextVar

from mcpauth import AuthInfo, MCPAuth, ResourceServerConfig
from mcpauth.config import AuthServerConfig, AuthServerType
from mcpauth.types import ResourceServerMetadata
from mcpauth.utils import fetch_server_config

DEFAULT_RESOURCE_URL = "http://localhost:8100/mcp"
DEFAULT_ISSUER_URL = "http://localhost:8000"
RESOURCE_URL_VAR = "MCP_RESOURCE_URL"
ISSUER_URL_VAR = "MCP_AUTH_ISSUER_URL"
JWKS_URI_VAR = "MCP_AUTH_JWKS_URI"

# Scopes this server understands (advertised in PRM; enforced per tool).
SUPPORTED_SCOPES: tuple[str, ...] = (
    "incidents:read",
    "incidents:write",
    "inventory:read",
)

# Verified identity for the request being processed. Set by the MCP Auth
# bearer middleware before the MCP transport runs; ``None`` = unauthenticated
# (fail closed everywhere it is read).
AUTH_CONTEXT: ContextVar[AuthInfo | None] = ContextVar(
    "mcp_auth_context", default=None
)


def resource_url() -> str:
    """Public identifier of this MCP resource (RFC 8707 audience)."""
    return os.getenv(RESOURCE_URL_VAR, DEFAULT_RESOURCE_URL).rstrip("/")


def issuer_url() -> str:
    """Authorization server whose discovery document is fetched at startup."""
    return os.getenv(ISSUER_URL_VAR, DEFAULT_ISSUER_URL).rstrip("/")


def load_auth_server_config() -> AuthServerConfig:
    """Fetch ``{issuer}/.well-known/openid-configuration`` (sync, at startup).

    ``MCP_AUTH_JWKS_URI`` (optional) replaces the ``jwks_uri`` the discovery
    document advertises: the token ``iss`` must remain the public issuer, but
    the JWKS document may only be reachable on the compose network.
    """
    config = fetch_server_config(issuer_url(), AuthServerType.OIDC)
    jwks_override = os.getenv(JWKS_URI_VAR, "").strip()
    if jwks_override:
        config.metadata.jwks_uri = jwks_override
    return config


def build_mcp_auth() -> MCPAuth:
    """MCP Auth instance: protected-resource metadata + bearer verification.

    ``fetch_server_config`` runs here, so the authorization server must be
    reachable when the ASGI app is built (``app.create_app``).
    """
    return MCPAuth(
        protected_resources=[
            ResourceServerConfig(
                metadata=ResourceServerMetadata(
                    resource=resource_url(),
                    resource_name="HealthCore incidents + inventory MCP",
                    authorization_servers=[load_auth_server_config()],
                    scopes_supported=list(SUPPORTED_SCOPES),
                    bearer_methods_supported=["header"],
                )
            )
        ],
        context_var=AUTH_CONTEXT,
    )


def bearer_middleware(mcp_auth: MCPAuth):
    """Bearer-auth middleware class for the MCP transport mount.

    JWT mode: JWKS verification + ``iss`` check by MCP Auth; ``aud`` must be
    this resource (RFC 8707). Per-tool scopes are enforced in
    :mod:`permissions`, so no transport-wide ``required_scopes``.
    """
    return mcp_auth.bearer_auth_middleware(
        "jwt",
        resource=resource_url(),
        audience=resource_url(),
    )


__all__ = [
    "AUTH_CONTEXT",
    "SUPPORTED_SCOPES",
    "bearer_middleware",
    "build_mcp_auth",
    "issuer_url",
    "load_auth_server_config",
    "resource_url",
]
