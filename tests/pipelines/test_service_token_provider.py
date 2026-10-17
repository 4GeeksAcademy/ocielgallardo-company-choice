"""Unit tests for the auto-renewing client-credentials token provider (§9.1).

Offline: ``httpx.post`` and the clock are monkeypatched — no backend required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import httpx  # noqa: E402

import data.pipelines.service_token_provider as provider  # noqa: E402
from data.pipelines.service_token_provider import (  # noqa: E402
    REFRESH_MARGIN_SECONDS,
    ServiceTokenProvider,
)


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _grant_response(token: str = "service-jwt", expires_in: int = 900) -> _FakeResponse:
    return _FakeResponse(
        {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "scope": "incidents:read inventory:read",
        }
    )


def _configure_env(monkeypatch, secret: str = "client-secret-value") -> None:
    monkeypatch.setenv("AGENT_TOOL_API_URL", "http://api.test:8000")
    monkeypatch.setenv("AGENT_TOOL_CLIENT_ID", "langgraph-agent")
    monkeypatch.setenv("AGENT_TOOL_CLIENT_SECRET", secret)
    monkeypatch.delenv("AGENT_TOOL_CLIENT_SECRET_FILE", raising=False)


def _fake_clock(monkeypatch, start: float) -> dict:
    now = {"t": start}
    monkeypatch.setattr(provider, "time", SimpleNamespace(time=lambda: now["t"]))
    return now


def test_missing_credentials_returns_none_without_http(monkeypatch) -> None:
    calls: list = []
    monkeypatch.setenv("AGENT_TOOL_API_URL", "http://api.test:8000")
    monkeypatch.delenv("AGENT_TOOL_CLIENT_ID", raising=False)
    monkeypatch.delenv("AGENT_TOOL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("AGENT_TOOL_CLIENT_SECRET_FILE", raising=False)
    monkeypatch.setattr(
        provider.httpx, "post", lambda *a, **k: calls.append(a) or _grant_response()
    )

    token = ServiceTokenProvider().get_token()

    assert token is None
    assert calls == []


def test_fetch_posts_grant_and_caches_until_refresh_margin(monkeypatch) -> None:
    _configure_env(monkeypatch)
    _fake_clock(monkeypatch, start=1000.0)
    calls: list[dict] = []

    def _post(url, *, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _grant_response(token="tok-1", expires_in=900)

    monkeypatch.setattr(provider.httpx, "post", _post)
    provider_instance = ServiceTokenProvider()

    first = provider_instance.get_token()

    assert first == "tok-1"
    assert len(calls) == 1
    assert calls[0]["url"] == "http://api.test:8000/auth/token"
    assert calls[0]["json"] == {
        "grant_type": "client_credentials",
        "client_id": "langgraph-agent",
        "client_secret": "client-secret-value",
    }
    assert calls[0]["timeout"] == 5.0

    # Well before the margin: cached token is reused, no new HTTP call.
    clock = {"t": 1000.0 + 60.0}
    monkeypatch.setattr(provider, "time", SimpleNamespace(time=lambda: clock["t"]))
    assert provider_instance.get_token() == "tok-1"
    assert len(calls) == 1


def test_refetches_inside_refresh_margin(monkeypatch) -> None:
    _configure_env(monkeypatch)
    _fake_clock(monkeypatch, start=1000.0)
    calls = {"n": 0}

    def _post(url, *, json, timeout):
        calls["n"] += 1
        return _grant_response(token=f"tok-{calls['n']}", expires_in=900)

    monkeypatch.setattr(provider.httpx, "post", _post)
    provider_instance = ServiceTokenProvider()

    assert provider_instance.get_token() == "tok-1"

    # 100 s before expiry → inside the 120 s margin → automatic renewal.
    clock = {"t": 1000.0 + 900.0 - 100.0}
    monkeypatch.setattr(provider, "time", SimpleNamespace(time=lambda: clock["t"]))

    assert provider_instance.get_token() == "tok-2"
    assert calls["n"] == 2


def test_keeps_previous_token_when_renewal_fails(monkeypatch) -> None:
    _configure_env(monkeypatch)
    _fake_clock(monkeypatch, start=1000.0)
    responses = [
        _grant_response(token="tok-1", expires_in=900),
        _FakeResponse({"detail": "boom"}, 500),
    ]

    def _post(*args, **kwargs):
        if responses:
            return responses.pop(0)
        return _FakeResponse({"detail": "boom"}, 500)

    monkeypatch.setattr(provider.httpx, "post", _post)
    provider_instance = ServiceTokenProvider()

    assert provider_instance.get_token() == "tok-1"

    # Renewal fails inside the margin, but the old token is still strictly
    # valid → keep serving it (grace) instead of dropping auth entirely.
    clock = {"t": 1000.0 + 900.0 - 30.0}
    monkeypatch.setattr(provider, "time", SimpleNamespace(time=lambda: clock["t"]))
    assert provider_instance.get_token() == "tok-1"

    # Past absolute expiry with renewal failing → None (tools lose auth and
    # surface an explicit auth error on the next API call).
    clock["t"] = 1000.0 + 900.0 + 1.0
    assert provider_instance.get_token() is None


def test_grant_rejection_returns_none(monkeypatch) -> None:
    _configure_env(monkeypatch)
    _fake_clock(monkeypatch, start=1000.0)
    monkeypatch.setattr(
        provider.httpx, "post", lambda *a, **k: _FakeResponse({}, 401)
    )

    assert ServiceTokenProvider().get_token() is None


def test_grant_timeout_returns_none(monkeypatch) -> None:
    _configure_env(monkeypatch)

    def _timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out", request=None)

    monkeypatch.setattr(provider.httpx, "post", _timeout)

    assert ServiceTokenProvider().get_token() is None


def test_non_json_grant_body_returns_none(monkeypatch) -> None:
    _configure_env(monkeypatch)
    monkeypatch.setattr(
        provider.httpx,
        "post",
        lambda *a, **k: _FakeResponse(ValueError("not json"), 200),
    )

    assert ServiceTokenProvider().get_token() is None


def test_secret_file_indirection_preferred_over_env(monkeypatch, tmp_path) -> None:
    secret_file = tmp_path / "client_secret"
    secret_file.write_text("secret-from-mounted-file\n", encoding="utf-8")
    _configure_env(monkeypatch, secret="env-should-not-be-used")
    monkeypatch.setenv("AGENT_TOOL_CLIENT_SECRET_FILE", str(secret_file))
    seen: dict = {}

    def _post(url, *, json, timeout):
        seen.update(json)
        return _grant_response()

    monkeypatch.setattr(provider.httpx, "post", _post)

    assert ServiceTokenProvider().get_token() == "service-jwt"
    assert seen["client_secret"] == "secret-from-mounted-file"


def test_provider_source_posts_only_to_the_auth_token_route() -> None:
    """Static guard: the provider never touches business-data endpoints."""
    source = Path(provider.__file__).read_text(encoding="utf-8")

    assert source.count("httpx.post") == 1
    assert "/auth/token" in source
    for forbidden in (
        ".patch(",
        ".put(",
        ".delete(",
        "httpx.get",
        "httpx.patch",
        "httpx.put",
        "httpx.delete",
    ):
        assert forbidden not in source


def test_refresh_margin_is_explicit() -> None:
    assert REFRESH_MARGIN_SECONDS == 120.0
