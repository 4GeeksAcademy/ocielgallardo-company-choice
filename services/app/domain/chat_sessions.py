"""In-memory Compliance assistant chat sessions + per-session pub/sub.

BRIEFING Part 2: ChatSession fields and event fan-out over ``chat.<session_id>``.
No PHI. No RFP/SSE schemas.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

AGENT_ID_COMPLIANCE = "compliance_assistant"

SessionStatus = str  # active | interrupted | closed


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_session_id() -> str:
    return f"chat_{uuid.uuid4().hex[:8]}"


def new_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:8]}"


@dataclass
class ChatMessage:
    message_id: str
    role: str  # user | assistant
    text: str
    status: str = "complete"  # complete | interrupted


@dataclass
class ChatSession:
    session_id: str
    agent_id: str
    user_id: str
    status: SessionStatus
    created_at: datetime
    messages: list[ChatMessage] = field(default_factory=list)


@dataclass
class GenerationHandle:
    """Cancel flag for the active generation on a session."""

    message_id: str
    cancel_event: threading.Event = field(default_factory=threading.Event)
    sequence: int = 0

    def request_cancel(self) -> None:
        self.cancel_event.set()

    def cancelled(self) -> bool:
        return self.cancel_event.is_set()


class ChatSessionStore:
    """Process-local session store + asyncio pub/sub per session."""

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}
        self._generations: dict[str, GenerationHandle] = {}
        self._loop_lock = threading.Lock()

    def channel_name(self, session_id: str) -> str:
        return f"chat.{session_id}"

    def create_session(self, *, user_id: str) -> ChatSession:
        session = ChatSession(
            session_id=new_session_id(),
            agent_id=AGENT_ID_COMPLIANCE,
            user_id=str(user_id),
            status="active",
            created_at=_utc_now(),
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_or_create_for_user(
        self, *, session_id: str | None, user_id: str
    ) -> ChatSession:
        if session_id:
            existing = self.get_session(session_id)
            if existing is not None and existing.user_id == str(user_id):
                return existing
        return self.create_session(user_id=user_id)

    def set_status(self, session_id: str, status: SessionStatus) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                session.status = status

    def append_message(
        self,
        session_id: str,
        *,
        role: str,
        text: str,
        status: str = "complete",
        message_id: str | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            message_id=message_id or new_message_id(),
            role=role,
            text=text,
            status=status,
        )
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"unknown session_id={session_id}")
            session.messages.append(msg)
        return msg

    def snapshot_payload(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"unknown session_id={session_id}")
        return {
            "session_id": session.session_id,
            "messages": [
                {
                    "message_id": m.message_id,
                    "role": m.role,
                    "text": m.text,
                    "status": m.status,
                }
                for m in session.messages
            ],
        }

    def begin_generation(self, session_id: str) -> GenerationHandle:
        handle = GenerationHandle(message_id=new_message_id())
        with self._lock:
            self._generations[session_id] = handle
            session = self._sessions.get(session_id)
            if session is not None:
                session.status = "active"
        return handle

    def get_generation(self, session_id: str) -> GenerationHandle | None:
        with self._lock:
            return self._generations.get(session_id)

    def clear_generation(self, session_id: str) -> None:
        with self._lock:
            self._generations.pop(session_id, None)

    def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        with self._loop_lock:
            self._subscribers.setdefault(session_id, []).append(queue)
        return queue

    def unsubscribe(
        self, session_id: str, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        with self._loop_lock:
            subs = self._subscribers.get(session_id) or []
            if queue in subs:
                subs.remove(queue)
            if not subs and session_id in self._subscribers:
                del self._subscribers[session_id]

    def publish(self, session_id: str, event: str, data: dict[str, Any]) -> None:
        """Publish to all WS subscribers of ``chat.<session_id>``."""
        envelope = {"event": event, "data": data}
        with self._loop_lock:
            subs = list(self._subscribers.get(session_id) or [])
        for queue in subs:
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                pass


# Process singleton
chat_store = ChatSessionStore()


def frame(event: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"event": event, "data": data}
