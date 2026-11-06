"""Reproducible rate-limit proof for POST /agent/query (no live LLM)."""

from __future__ import annotations

import os
import sys
import types
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-not-for-prod")

if "pywintypes" not in sys.modules:
    sys.modules["pywintypes"] = types.SimpleNamespace()
sys.modules.setdefault("langchain_mcp_adapters", MagicMock())
sys.modules.setdefault("langchain_mcp_adapters.client", MagicMock())

from services.app.core import rate_limit as rate_limit_module  # noqa: E402
from services.app.core.deps import get_current_user  # noqa: E402
from services.app.models.user import UserPublic, UserRole  # noqa: E402
from services.app.routers import agent as agent_module  # noqa: E402


def _staff_user() -> UserPublic:
    return UserPublic(
        id=42,
        email="claire@healthcore.example",
        role=UserRole.MANAGER,
        is_active=True,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def agent_client(monkeypatch):
    rate_limit_module.agent_query_limiter.reset()
    monkeypatch.setenv("AGENT_QUERY_RATE_LIMIT", "3")
    monkeypatch.setenv("AGENT_QUERY_RATE_WINDOW_SECONDS", "60")

    monkeypatch.setattr(
        agent_module,
        "run_agent",
        MagicMock(return_value={"answer": "policy answer", "trace_id": "t-test"}),
    )

    application = FastAPI()
    application.include_router(agent_module.router)
    application.dependency_overrides[get_current_user] = _staff_user
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()
    rate_limit_module.agent_query_limiter.reset()


def test_agent_query_returns_429_after_limit(agent_client: TestClient) -> None:
    payload = {"question": "What documents do new patients need?"}
    for _ in range(3):
        ok = agent_client.post("/agent/query", json=payload)
        assert ok.status_code == 200, ok.text

    blocked = agent_client.post("/agent/query", json=payload)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert int(blocked.headers["Retry-After"]) >= 1
    assert "rate limit" in blocked.json()["detail"].lower()


def test_sliding_window_limiter_unit() -> None:
    limiter = rate_limit_module.SlidingWindowRateLimiter()
    for _ in range(2):
        assert limiter.check("k", limit=2, window_seconds=60).allowed is True
    denied = limiter.check("k", limit=2, window_seconds=60)
    assert denied.allowed is False
    assert denied.retry_after_seconds >= 1
