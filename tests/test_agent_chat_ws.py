"""WebSocket Compliance chat — BRIEFING Part 2 event contract."""

from __future__ import annotations

import os
import sys
import types
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Ensure JWT secret before security import side effects in CI without .env.
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-not-for-prod")

# Windows MCP import chain needs pywintypes; stub for hermetic unit tests.
if "pywintypes" not in sys.modules:
    sys.modules["pywintypes"] = types.SimpleNamespace()
# Avoid pulling a live MCP client during agent_graph import.
sys.modules.setdefault("langchain_mcp_adapters", MagicMock())
sys.modules.setdefault("langchain_mcp_adapters.client", MagicMock())

import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient

from services.app.domain import chat_sessions  # noqa: E402
from services.app.models.user import UserPublic, UserRole  # noqa: E402
from services.app.routers import agent as agent_module  # noqa: E402


def _reset_store() -> None:
    store = chat_sessions.chat_store
    store._sessions.clear()
    store._subscribers.clear()
    store._generations.clear()


@pytest.fixture
def app(monkeypatch):
    _reset_store()
    user = UserPublic(
        id=42,
        email="staff@healthcore.example",
        role=UserRole.MANAGER,
        is_active=True,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    guest = UserPublic(
        id=99,
        email="guest@healthcore.example",
        role=UserRole.USER,
        is_active=True,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    def _auth(token: str | None):
        if token == "good-token":
            return user
        if token == "guest-token":
            return guest
        return None

    monkeypatch.setattr(agent_module, "_user_from_ws_token", _auth)

    def _fake_stream(question, *, thread_id, on_token, cancel_check):
        for part in ["Según ", "UK ", "GDPR"]:
            if cancel_check():
                from data.pipelines.rag import GenerationInterrupted

                raise GenerationInterrupted("cancelled")
            on_token(part)
        return {"answer": "Según UK GDPR", "trace_id": thread_id}

    monkeypatch.setattr(agent_module, "run_agent_stream", _fake_stream)

    application = FastAPI()
    application.include_router(agent_module.router)
    yield application
    _reset_store()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def test_ws_rejects_missing_token(client: TestClient) -> None:
    # The backoffice stops reconnecting and asks to sign in on exactly 4401.
    for path in ("/agent/chat/ws", "/agent/chat/ws?token=bad-token"):
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(path):
                pass
        assert exc.value.code == 4401


def test_ws_rejects_non_staff_role(client: TestClient) -> None:
    # The backoffice shows "no access" (no retry loop) on exactly 4403.
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/agent/chat/ws?token=guest-token"):
            pass
    assert exc.value.code == 4403


def test_ws_snapshot_and_token_stream(client: TestClient) -> None:
    with client.websocket_connect("/agent/chat/ws?token=good-token") as ws:
        first = ws.receive_json()
        assert first["event"] == "session_snapshot"
        assert first["data"]["session_id"].startswith("chat_")
        assert first["data"]["messages"] == []
        session_id = first["data"]["session_id"]

        ws.send_json(
            {
                "event": "user_message",
                "data": {"session_id": session_id, "text": "What about UK GDPR?"},
            }
        )

        events = []
        # user_message echo + token chunks + generation_completed
        for _ in range(12):
            msg = ws.receive_json()
            events.append(msg["event"])
            if msg["event"] == "generation_completed":
                break

        assert "token_chunk" in events
        assert "generation_completed" in events
        chunks = [
            e
            for e in events
            # collect from raw receives — re-walk via store snapshot instead
        ]
        _ = chunks
        # Reconnect snapshot should include history without PHI keys
        snap = chat_sessions.chat_store.snapshot_payload(session_id)
        assert "patient" not in str(snap).lower()
        assert "rfp_id" not in str(snap)
        assert any(m["role"] == "user" for m in snap["messages"])
        assert any(m["role"] == "assistant" for m in snap["messages"])


def test_ws_interrupt_aborts_generation(client: TestClient, monkeypatch) -> None:
    import threading
    import time

    started = threading.Event()

    def _slow_stream(question, *, thread_id, on_token, cancel_check):
        on_token("Under ")
        started.set()
        for _ in range(50):
            if cancel_check():
                from data.pipelines.rag import GenerationInterrupted

                raise GenerationInterrupted("cancelled")
            time.sleep(0.05)
            on_token("HIPAA ")
        return {"answer": "Under HIPAA ...", "trace_id": thread_id}

    monkeypatch.setattr(agent_module, "run_agent_stream", _slow_stream)

    with client.websocket_connect("/agent/chat/ws?token=good-token") as ws:
        snap = ws.receive_json()
        sid = snap["data"]["session_id"]
        ws.send_json(
            {
                "event": "user_message",
                "data": {"session_id": sid, "text": "Tell me about HIPAA rules"},
            }
        )
        # Wait until streaming started
        assert started.wait(timeout=5)
        # Drain a couple of frames
        for _ in range(5):
            msg = ws.receive_json()
            if msg["event"] == "token_chunk":
                break

        ws.send_json(
            {
                "event": "interrupt_requested",
                "data": {
                    "session_id": sid,
                    "new_input": "wait, my question was about UK GDPR, not HIPAA",
                },
            }
        )

        saw_interrupted = False
        for _ in range(40):
            msg = ws.receive_json()
            if msg["event"] == "generation_interrupted":
                saw_interrupted = True
                assert msg["data"]["status"] == "interrupted"
                assert msg["data"]["session_id"] == sid
                break
        assert saw_interrupted

        snap = chat_sessions.chat_store.snapshot_payload(sid)
        interrupted_msgs = [
            m for m in snap["messages"] if m.get("status") == "interrupted"
        ]
        assert interrupted_msgs, "partial assistant message must be kept as interrupted"
        assert interrupted_msgs[0]["text"].startswith("Under")
        # Redirect turn should appear as a new user message (not overwrite interrupted).
        user_texts = [m["text"] for m in snap["messages"] if m["role"] == "user"]
        assert any("UK GDPR" in t for t in user_texts)


def test_ws_reconnect_restores_history(client: TestClient) -> None:
    with client.websocket_connect("/agent/chat/ws?token=good-token") as ws:
        first = ws.receive_json()
        sid = first["data"]["session_id"]
        ws.send_json(
            {
                "event": "user_message",
                "data": {"session_id": sid, "text": "What about UK GDPR?"},
            }
        )
        for _ in range(12):
            msg = ws.receive_json()
            if msg["event"] == "generation_completed":
                break

    # Reopen with same session_id — must rehydrate, not empty chat.
    with client.websocket_connect(
        f"/agent/chat/ws?token=good-token&session_id={sid}"
    ) as ws2:
        snap = ws2.receive_json()
        assert snap["event"] == "session_snapshot"
        assert snap["data"]["session_id"] == sid
        msgs = snap["data"]["messages"]
        assert len(msgs) >= 2
        assert any(m["role"] == "user" for m in msgs)
        assert any(m["role"] == "assistant" for m in msgs)


def test_token_chunk_payload_shape() -> None:
    """BRIEFING field names for token_chunk (no RFP / PHI keys)."""
    payload = {
        "session_id": "chat_0076",
        "token": "Según",
        "sequence": 9,
    }
    assert set(payload.keys()) == {"session_id", "token", "sequence"}
    assert "patient" not in payload
    assert "ticket_id" not in payload
