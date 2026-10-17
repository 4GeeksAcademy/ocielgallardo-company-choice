"""Service (machine) identity for internal API tool callers.

Implements an OAuth2 *client-credentials* style grant for non-human callers
(design baseline: ``docs/rag/agent-graph.md`` §9.1):

- ``POST /auth/token`` exchanges ``client_id`` + ``client_secret`` for a
  short-lived JWT with ``typ=service`` and read-only scopes.
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

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import jwt
from tinydb import Query

from services.app.core.database import service_clients_table
from services.app.core.security import ALGORITHM, SECRET_KEY, pwd_context

SERVICE_TOKEN_TYPE = "service"
DEFAULT_SERVICE_SCOPES: tuple[str, ...] = ("incidents:read", "inventory:read")
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


def create_service_token(client_id: str, scopes: tuple[str, ...] | list[str]) -> str:
    """Mint a short-lived service JWT (never handed to humans)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": f"svc:{client_id}",
        "typ": SERVICE_TOKEN_TYPE,
        "scope": " ".join(scopes),
        "iat": now,
        "exp": now + timedelta(minutes=SERVICE_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def grant_client_credentials(
    client_id: str, client_secret: str
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
        access_token=create_service_token(client_id, scopes),
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
