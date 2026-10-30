"""HTTP-level test for GET /rfp/events/stream (minimal app, mocked events)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services.app.core.deps import get_current_user
from services.app.domain.rfp_sse import (
    RFP_TICKET_CREATED_EVENT,
    build_rfp_ticket_created_payload,
    format_sse_message,
)
from services.app.models.user import UserPublic, UserRole
from services.app.routers.rfp import router as rfp_router


async def _fake_events() -> AsyncIterator[str]:
    payload = build_rfp_ticket_created_payload(
        ticket_id="stream-ticket-1",
        metadata={"client_name": "Stream Co", "client_country": "US"},
        status="analyzing",
        created_at="2026-07-24T14:32:00Z",
    )
    yield format_sse_message(event=RFP_TICKET_CREATED_EVENT, data=payload)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        "services.app.routers.rfp.iter_rfp_sse_events",
        lambda: _fake_events(),
    )

    def _fake_user() -> UserPublic:
        return UserPublic(
            id=1,
            email="sse@healthcore.example",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    app = FastAPI()
    app.include_router(rfp_router)
    app.dependency_overrides[get_current_user] = _fake_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_rfp_events_stream_emits_ticket_created(client: TestClient) -> None:
    with client.stream("GET", "/rfp/events/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        chunks: list[str] = []
        for line in response.iter_lines():
            chunks.append(line)
            if len(chunks) > 20:
                break
        body = "\n".join(chunks)
        assert "event: rfp_ticket_created" in body
        assert "stream-ticket-1" in body
        assert "Stream Co" in body
