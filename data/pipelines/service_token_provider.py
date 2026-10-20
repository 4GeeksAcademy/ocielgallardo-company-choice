"""Auto-renewing client-credentials token provider for agent tool calls.

Exchanges ``AGENT_TOOL_CLIENT_ID`` / ``AGENT_TOOL_CLIENT_SECRET`` for a
short-lived service JWT via ``POST /auth/token`` and caches it until shortly
before expiry, so more than 24 h of continuous operation needs no human
intervention (acceptance criteria: ``docs/rag/agent-graph.md`` §9.1).

This module issues the only HTTP POST in the agent data path: an auth grant
against ``/auth/token``. Business data itself is reached over MCP only
(``data/pipelines/mcp_client.py``), never with direct HTTP calls from the
agent (``agent_tools.py`` holds contracts and formatters, statically guarded).

Credentials come from environment/config — never hardcoded:

- ``AGENT_TOOL_API_URL`` — API base URL (default ``http://127.0.0.1:8000``).
- ``AGENT_TOOL_CLIENT_ID`` — service client id (or ``..._FILE`` path).
- ``AGENT_TOOL_CLIENT_SECRET`` — service client secret; in Docker prefer
  ``AGENT_TOOL_CLIENT_SECRET_FILE`` pointing at a mounted secret.

The same provider serves other service identities (e.g. the MCP server, which
authenticates to the same API) by passing its own credential prefix:
``get_service_token("MCP_BACKEND", "MCP_BACKEND_URL")`` reads
``MCP_BACKEND_CLIENT_ID`` / ``MCP_BACKEND_CLIENT_SECRET`` against the URL in
``MCP_BACKEND_URL``.

Audience (RFC 8707): the MCP client mints its agent token with
``audience=<MCP_RESOURCE_URL>`` so the MCP resource server can require it;
tokens without an audience keep working for callers that do not check it (the
API itself does not validate ``aud`` — that is the resource server's job).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_CREDENTIAL_PREFIX = "AGENT_TOOL"
DEFAULT_API_URL_VAR = "AGENT_TOOL_API_URL"
TOKEN_TIMEOUT_SECONDS = 5.0
# Renew before expiry so in-flight calls never race the TTL.
REFRESH_MARGIN_SECONDS = 120.0


def api_base_url(var: str = DEFAULT_API_URL_VAR) -> str:
    """Base URL of the HealthCore API (env, never hardcoded)."""
    return os.getenv(var, DEFAULT_API_BASE_URL).rstrip("/")


def _read_credential(name: str) -> str:
    """Credential from ``<name>_FILE`` (mounted secret) or plain env fallback."""
    file_path = os.getenv(f"{name}_FILE", "").strip()
    if file_path:
        try:
            return Path(file_path).read_text(encoding="utf-8").strip()
        except OSError:
            logger.error(
                "Could not read %s_FILE (%s); falling back to env",
                name,
                file_path,
            )
    return os.getenv(name, "").strip()


class ServiceTokenProvider:
    """Thread-safe cached service token with automatic renewal.

    ``credential_prefix`` selects which identity is used (``AGENT_TOOL`` by
    default; the MCP server uses ``MCP_BACKEND``), so several service
    identities can coexist in one process without sharing tokens. When
    ``audience`` is set it is forwarded to ``POST /auth/token`` (``aud`` claim),
    which is what the MCP resource server validates; cached tokens are keyed by
    prefix + URL + audience, so different audiences never share a cache entry.
    """

    def __init__(
        self,
        credential_prefix: str = DEFAULT_CREDENTIAL_PREFIX,
        api_url_var: str = DEFAULT_API_URL_VAR,
        audience: str | None = None,
    ) -> None:
        self._credential_prefix = credential_prefix
        self._api_url_var = api_url_var
        self._audience = audience
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get_token(self) -> str | None:
        """Return a valid (cached) service token, or None when unavailable."""
        now = time.time()
        with self._lock:
            if self._token and now < self._expires_at - REFRESH_MARGIN_SECONDS:
                return self._token
            fresh = self._fetch_token(now)
            if fresh is not None:
                self._token, self._expires_at = fresh
            # On renewal failure keep serving the previous token while it is
            # still strictly valid (grace inside the refresh margin).
            if self._token and now < self._expires_at:
                return self._token
            return None

    def _fetch_token(self, now: float) -> tuple[str, float] | None:
        client_id = _read_credential(f"{self._credential_prefix}_CLIENT_ID")
        client_secret = _read_credential(f"{self._credential_prefix}_CLIENT_SECRET")
        if not client_id or not client_secret:
            logger.warning(
                "Service credentials not configured "
                "(%s_CLIENT_ID / %s_CLIENT_SECRET); "
                "agent tool calls will lack auth",
                self._credential_prefix,
                self._credential_prefix,
            )
            return None
        try:
            body = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
            if self._audience:
                body["audience"] = self._audience
            response = httpx.post(
                f"{api_base_url(self._api_url_var)}/auth/token",
                json=body,
                timeout=TOKEN_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException:
            logger.error(
                "Service token grant timed out after %.1fs",
                TOKEN_TIMEOUT_SECONDS,
            )
            return None
        except httpx.HTTPError:
            logger.exception("Service token grant failed (transport)")
            return None
        if response.status_code != 200:
            logger.error(
                "Service token grant rejected: HTTP %s "
                "(client id unknown, secret wrong, or client revoked)",
                response.status_code,
            )
            return None
        try:
            payload = response.json()
        except ValueError:
            logger.error("Service token grant returned a non-JSON body")
            return None
        token = str(payload.get("access_token") or "")
        if not token:
            logger.error("Service token grant returned no access_token")
            return None
        expires_in = float(payload.get("expires_in") or 0)
        logger.info("Service token renewed (expires_in=%.0fs)", expires_in)
        return token, now + expires_in


_providers: dict[str, ServiceTokenProvider] = {}
_providers_lock = threading.Lock()
_agent_provider = ServiceTokenProvider()


def get_service_token(
    credential_prefix: str = DEFAULT_CREDENTIAL_PREFIX,
    api_url_var: str = DEFAULT_API_URL_VAR,
    audience: str | None = None,
) -> str | None:
    """Shared provider entry point used by service identities.

    The default call returns the agent identity token without an audience
    (unchanged behavior); the MCP client passes ``audience=<resource url>`` so
    the minted token satisfies the MCP resource server's ``aud`` check. Pass a
    different ``credential_prefix`` for another service identity (the MCP
    server uses ``MCP_BACKEND`` + ``MCP_BACKEND_URL``).
    """
    if (
        credential_prefix == DEFAULT_CREDENTIAL_PREFIX
        and api_url_var == DEFAULT_API_URL_VAR
        and audience is None
    ):
        return _agent_provider.get_token()
    key = f"{credential_prefix}|{api_url_var}|{audience or ''}"
    with _providers_lock:
        provider = _providers.get(key)
        if provider is None:
            provider = ServiceTokenProvider(credential_prefix, api_url_var, audience)
            _providers[key] = provider
    return provider.get_token()
