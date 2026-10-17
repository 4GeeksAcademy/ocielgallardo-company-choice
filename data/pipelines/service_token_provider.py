"""Auto-renewing client-credentials token provider for agent tool calls.

Exchanges ``AGENT_TOOL_CLIENT_ID`` / ``AGENT_TOOL_CLIENT_SECRET`` for a
short-lived service JWT via ``POST /auth/token`` and caches it until shortly
before expiry, so more than 24 h of continuous operation needs no human
intervention (acceptance criteria: ``docs/rag/agent-graph.md`` §9.1).

This module issues the only HTTP POST made by the agent tools: an auth grant
against ``/auth/token``. Business-data access stays GET-only in
``agent_tools.py`` (statically guarded there).

Credentials come from environment/config — never hardcoded:

- ``AGENT_TOOL_API_URL`` — API base URL (default ``http://127.0.0.1:8000``).
- ``AGENT_TOOL_CLIENT_ID`` — service client id (or ``..._FILE`` path).
- ``AGENT_TOOL_CLIENT_SECRET`` — service client secret; in Docker prefer
  ``AGENT_TOOL_CLIENT_SECRET_FILE`` pointing at a mounted secret.
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
TOKEN_TIMEOUT_SECONDS = 5.0
# Renew before expiry so in-flight calls never race the TTL.
REFRESH_MARGIN_SECONDS = 120.0


def api_base_url() -> str:
    """Base URL of the HealthCore API (env, never hardcoded)."""
    return os.getenv("AGENT_TOOL_API_URL", DEFAULT_API_BASE_URL).rstrip("/")


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
    """Thread-safe cached service token with automatic renewal."""

    def __init__(self) -> None:
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
        client_id = _read_credential("AGENT_TOOL_CLIENT_ID")
        client_secret = _read_credential("AGENT_TOOL_CLIENT_SECRET")
        if not client_id or not client_secret:
            logger.warning(
                "Service credentials not configured "
                "(AGENT_TOOL_CLIENT_ID / AGENT_TOOL_CLIENT_SECRET); "
                "agent tool calls will lack auth"
            )
            return None
        try:
            response = httpx.post(
                f"{api_base_url()}/auth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
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


_provider = ServiceTokenProvider()


def get_service_token() -> str | None:
    """Shared provider entry point used by the agent tools' auth headers."""
    return _provider.get_token()
