"""Service (machine) identity for internal API tool callers.

Implements an OAuth2 *client-credentials* style grant for non-human callers
(design baseline: ``docs/rag/agent-graph.md`` §9.1):

- ``POST /auth/token`` exchanges ``client_id`` + ``client_secret`` for a
  short-lived JWT with ``typ=service`` and read-only scopes.
- Service tokens are signed **RS256** by :mod:`services.app.core.oauth_keys`
  and carry ``iss``/``aud``/``kid`` so resource servers (the MCP server via
  ``mcpauth``) can verify them from ``/.well-known/jwks.json`` — the symmetric
  ``SECRET_KEY`` only ever signs human sessions.
- Protected routes verify the signature, the ``service`` type marker, and
  that the client is still registered (immediate revocation).
- Human user JWTs (``sub`` = integer user id, no ``typ`` claim) are never
  treated as service tokens, and service tokens are rejected by the regular
  ``get_current_user`` dependency (fail closed outside the scoped routes).

Secrets are stored bcrypt-hashed in the TinyDB ``service_clients`` table
(same store as auth). Registration/rotation:
``PYTHONPATH=. uv run python scripts/seed_service_client.py``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import jwt
from tinydb import Query

from services.app.core import oauth_keys
from services.app.core.database import service_clients_table
from services.app.core.security import (
    OAUTH_DEFAULT_AUDIENCE,
    OAUTH_ISSUER_URL,
    SERVICE_ALGORITHM,
    SERVICE_TOKEN_TYPE,
    pwd_context,
)

DEFAULT_SERVICE_SCOPES: tuple[str, ...] = ("incidents:read", "inventory:read")
# The MCP server writes incidents on behalf of its tools (create/transition).
MCP_BACKEND_SCOPES: tuple[str, ...] = (
    "incidents:read",
    "incidents:write",
    "inventory:read",
)
# Service identities that can be registered from env at API startup:
# (credential prefix, scopes for a fresh registration).
ENV_SERVICE_IDENTITIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("AGENT_TOOL", DEFAULT_SERVICE_SCOPES),
    ("MCP_BACKEND", MCP_BACKEND_SCOPES),
)
BOOTSTRAP_FROM_ENV_VAR = "SERVICE_CLIENTS_FROM_ENV"

logger = logging.getLogger(__name__)
SERVICE_TOKEN_EXPIRE_MINUTES = int(os.getenv("SERVICE_TOKEN_EXPIRE_MINUTES", "15"))

_client_query = Query()


class ServiceTokenError(Exception):
    """Claims claim to be a service token but are invalid (shape/revocation)."""


@dataclass(frozen=True)
class ServicePrincipal:
    """Authenticated machine caller (never a human user account)."""

    client_id: str
    scopes: frozenset[str]

    @property
    def name(self) -> str:
        """Audit label used in API logs, e.g. ``svc:langgraph-agent``."""
        return f"svc:{self.client_id}"


@dataclass(frozen=True)
class ServiceTokenGrant:
    """Successful client-credentials grant (response body projection)."""

    access_token: str
    expires_in: int
    scope: str


def register_service_client(
    client_id: str,
    client_secret: str,
    scopes: tuple[str, ...] | list[str] = DEFAULT_SERVICE_SCOPES,
) -> None:
    """Create or replace a service client; the secret is stored hashed."""
    if not client_id.strip():
        raise ValueError("client_id must not be blank")
    if not client_secret:
        raise ValueError("client_secret must not be empty")
    service_clients_table.upsert(
        {
            "client_id": client_id.strip(),
            "secret_hash": pwd_context.hash(client_secret),
            "scopes": sorted(scopes),
        },
        _client_query.client_id == client_id.strip(),
    )


def unregister_service_client(client_id: str) -> None:
    """Remove a service client (immediate revocation of its tokens)."""
    service_clients_table.remove(_client_query.client_id == client_id)


def get_service_client(client_id: str) -> dict | None:
    """Return the registered client document or None."""
    rows = service_clients_table.search(_client_query.client_id == client_id)
    return rows[0] if rows else None


def _env_credential(name: str) -> str:
    """Credential from ``<name>_FILE`` (mounted secret) or the plain env var."""
    file_path = os.getenv(f"{name}_FILE", "").strip()
    if file_path:
        try:
            return Path(file_path).read_text(encoding="utf-8").strip()
        except OSError:
            logger.error("Could not read %s_FILE; falling back to env", name)
    return os.getenv(name, "").strip()


def _secret_matches(client: dict, client_secret: str) -> bool:
    try:
        return bool(
            pwd_context.verify(client_secret, str(client.get("secret_hash", "")))
        )
    except (TypeError, ValueError):
        return False


def bootstrap_enabled() -> bool:
    """True when the API should register service clients from env at startup."""
    return os.getenv(BOOTSTRAP_FROM_ENV_VAR, "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def bootstrap_service_clients_from_env() -> list[str]:
    """Register the agent/MCP service identities from env (Docker bootstrap).

    In Docker the auth store (TinyDB) lives inside the backend container, so a
    client seeded on the host with ``scripts/seed_service_client.py`` does not
    exist there and every ``POST /auth/token`` is rejected — the agent then
    never reaches the MCP server. With ``SERVICE_CLIENTS_FROM_ENV=true`` the API
    registers ``<PREFIX>_CLIENT_ID`` / ``<PREFIX>_CLIENT_SECRET`` (or
    ``..._FILE``) at startup. Idempotent: a client whose stored hash already
    matches the env secret is left untouched (scopes included). Secrets are
    never logged. Returns the client ids that were (re)registered.
    """
    registered: list[str] = []
    for prefix, scopes in ENV_SERVICE_IDENTITIES:
        client_id = _env_credential(f"{prefix}_CLIENT_ID")
        client_secret = _env_credential(f"{prefix}_CLIENT_SECRET")
        if not client_id or not client_secret:
            logger.warning(
                "Service client %s not bootstrapped: %s_CLIENT_ID / "
                "%s_CLIENT_SECRET not set",
                prefix,
                prefix,
                prefix,
            )
            continue
        existing = get_service_client(client_id)
        if existing is not None and _secret_matches(existing, client_secret):
            continue
        register_service_client(client_id, client_secret, scopes)
        registered.append(client_id)
        logger.info(
            "Service client %r registered from env (scopes: %s)",
            client_id,
            " ".join(scopes),
        )
    return registered


def create_service_token(
    client_id: str,
    scopes: tuple[str, ...] | list[str],
    *,
    audience: str | None = None,
) -> str:
    """Mint a short-lived RS256 service JWT (never handed to humans).

    ``aud`` defaults to ``OAUTH_TOKEN_AUDIENCE`` (else the issuer); callers
    targeting a specific resource (e.g. the MCP endpoint) pass it explicitly.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": f"svc:{client_id}",
        "typ": SERVICE_TOKEN_TYPE,
        "client_id": client_id,
        "scope": " ".join(scopes),
        "iss": OAUTH_ISSUER_URL,
        "aud": (audience or OAUTH_DEFAULT_AUDIENCE).rstrip("/"),
        "iat": now,
        "exp": now + timedelta(minutes=SERVICE_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(
        payload,
        oauth_keys.get_signing_pem(),
        algorithm=SERVICE_ALGORITHM,
        headers={"kid": oauth_keys.get_kid()},
    )


def grant_client_credentials(
    client_id: str, client_secret: str, *, audience: str | None = None
) -> ServiceTokenGrant | None:
    """Exchange client credentials for a service token; None = rejected."""
    client = get_service_client(client_id)
    if client is None:
        return None
    try:
        if not pwd_context.verify(client_secret, str(client.get("secret_hash", ""))):
            return None
    except (TypeError, ValueError):
        return None
    scopes = tuple(client.get("scopes") or DEFAULT_SERVICE_SCOPES)
    return ServiceTokenGrant(
        access_token=create_service_token(client_id, scopes, audience=audience),
        expires_in=SERVICE_TOKEN_EXPIRE_MINUTES * 60,
        scope=" ".join(scopes),
    )


def is_service_claims(payload: dict) -> bool:
    """True when decoded JWT claims are a service token (not a human session)."""
    return payload.get("typ") == SERVICE_TOKEN_TYPE


def service_principal_from_claims(payload: dict) -> ServicePrincipal:
    """Build the principal from claims; raise ServiceTokenError if unusable.

    A revoked (unregistered) client invalidates previously minted tokens on
    their next verification, before the short TTL runs out.
    """
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.startswith("svc:"):
        raise ServiceTokenError("service token has no 'svc:' subject")
    client_id = subject[len("svc:") :]
    if not client_id:
        raise ServiceTokenError("service token subject is empty")
    if get_service_client(client_id) is None:
        raise ServiceTokenError(f"service client {client_id!r} is not registered")
    raw_scope = payload.get("scope")
    scopes = frozenset(str(raw_scope).split()) if raw_scope else frozenset()
    return ServicePrincipal(client_id=client_id, scopes=scopes)


__all__ = [
    "DEFAULT_SERVICE_SCOPES",
    "ENV_SERVICE_IDENTITIES",
    "MCP_BACKEND_SCOPES",
    "bootstrap_enabled",
    "bootstrap_service_clients_from_env",
    "SERVICE_TOKEN_EXPIRE_MINUTES",
    "SERVICE_TOKEN_TYPE",
    "ServicePrincipal",
    "ServiceTokenError",
    "ServiceTokenGrant",
    "create_service_token",
    "get_service_client",
    "grant_client_credentials",
    "is_service_claims",
    "register_service_client",
    "service_principal_from_claims",
    "unregister_service_client",
]
