"""Agent endpoint (compiled LangGraph) + Compliance assistant WebSocket chat."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from jose import JWTError

from data.pipelines.agent_graph import run_agent, run_agent_stream
from data.pipelines.rag import GenerationInterrupted
from services.app.core.deps import get_current_user
from services.app.core.security import decode_token_claims
from services.app.core.service_identity import is_service_claims
from services.app.domain.chat_sessions import chat_store
from services.app.domain.user_service import UserNotFoundError, get_user_by_id
from services.app.models.user import UserPublic, UserRole
from services.app.schemas import RagQueryRequest, RagQueryResponse

_STAFF_ROLES = frozenset({UserRole.ADMIN, UserRole.MANAGER})

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=RagQueryResponse)
def query_agent(
    body: RagQueryRequest,
    _current_user: UserPublic = Depends(get_current_user),
) -> RagQueryResponse:
    """Answer a coordinator question through the compiled agent graph.

    Thin wrapper over ``run_agent()`` — no retrieval/generation logic here.
    Returns only the model-generated string (never raw chunks or scores).
    Returns 503 when the knowledge backend is unavailable; never a raw
    traceback.
    """
    try:
        answer = run_agent(body.question)["answer"]
    except RuntimeError as exc:
        logger.warning("Agent unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge assistant is temporarily unavailable.",
        ) from exc
    except Exception as exc:  # Qdrant connectivity, LLM transport, ...
        logger.exception(
            "Agent query failed (question_chars=%s)",
            len(body.question or ""),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge assistant is temporarily unavailable.",
        ) from exc
    return RagQueryResponse(question=body.question, answer=answer)


def _user_from_ws_token(token: str | None) -> UserPublic | None:
    if not token:
        return None
    try:
        claims = decode_token_claims(token)
        if is_service_claims(claims):
            return None
        user_id = int(claims.get("sub") or "")
        return get_user_by_id(user_id)
    except (JWTError, ValueError, TypeError, UserNotFoundError):
        return None


async def _send_event(websocket: WebSocket, event: str, data: dict[str, Any]) -> None:
    await websocket.send_json({"event": event, "data": data})


async def _pump_bus_to_ws(
    websocket: WebSocket,
    session_id: str,
    queue: asyncio.Queue,
    stop: asyncio.Event,
) -> None:
    while not stop.is_set():
        try:
            envelope = await asyncio.wait_for(queue.get(), timeout=0.5)
        except TimeoutError:
            continue
        try:
            await websocket.send_json(envelope)
        except Exception:  # noqa: BLE001 — socket closed
            break


def _run_generation_sync(
    *,
    session_id: str,
    question: str,
    handle_message_id: str,
) -> None:
    """Blocking worker: stream tokens onto the in-memory chat bus."""
    handle = chat_store.get_generation(session_id)
    if handle is None:
        return

    partial_parts: list[str] = []

    def on_token(tok: str) -> None:
        h = chat_store.get_generation(session_id)
        if h is None or h.cancelled():
            raise GenerationInterrupted("chat generation cancelled")
        h.sequence += 1
        partial_parts.append(tok)
        chat_store.publish(
            session_id,
            "token_chunk",
            {
                "session_id": session_id,
                "token": tok,
                "sequence": h.sequence,
            },
        )

    def cancel_check() -> bool:
        h = chat_store.get_generation(session_id)
        return h is None or h.cancelled()

    try:
        result = run_agent_stream(
            question,
            thread_id=session_id,
            on_token=on_token,
            cancel_check=cancel_check,
        )
        answer = (result.get("answer") or "".join(partial_parts)).strip()
        chat_store.append_message(
            session_id,
            role="assistant",
            text=answer,
            status="complete",
            message_id=handle_message_id,
        )
        chat_store.publish(
            session_id,
            "generation_completed",
            {"session_id": session_id, "message_id": handle_message_id},
        )
        chat_store.set_status(session_id, "active")
    except GenerationInterrupted:
        # Keep tokens already shown; do not overwrite/delete the interrupted msg.
        partial = "".join(partial_parts)
        chat_store.append_message(
            session_id,
            role="assistant",
            text=partial,
            status="interrupted",
            message_id=handle_message_id,
        )
        chat_store.set_status(session_id, "interrupted")
        chat_store.publish(
            session_id,
            "generation_interrupted",
            {
                "session_id": session_id,
                "message_id": handle_message_id,
                "status": "interrupted",
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("chat generation failed session_id=%s", session_id)
        chat_store.publish(
            session_id,
            "generation_interrupted",
            {
                "session_id": session_id,
                "message_id": handle_message_id,
                "status": "interrupted",
            },
        )
        chat_store.set_status(session_id, "interrupted")
    finally:
        chat_store.clear_generation(session_id)


@router.websocket("/chat/ws")
async def compliance_chat_ws(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
) -> None:
    """Bidirectional Compliance assistant chat (BRIEFING Part 2 events)."""
    user = _user_from_ws_token(token)
    if user is None:
        await websocket.close(code=4401)
        return
    if user.role not in _STAFF_ROLES:
        await websocket.close(code=4403)
        return

    await websocket.accept()
    session = chat_store.get_or_create_for_user(
        session_id=session_id, user_id=str(user.id)
    )
    sid = session.session_id
    queue = chat_store.subscribe(sid)
    stop_pump = asyncio.Event()
    pump_task = asyncio.create_task(_pump_bus_to_ws(websocket, sid, queue, stop_pump))
    gen_task: asyncio.Task | None = None

    try:
        await _send_event(websocket, "session_snapshot", chat_store.snapshot_payload(sid))

        while True:
            raw = await websocket.receive_text()
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError:
                continue
            event = envelope.get("event")
            data = envelope.get("data") or {}
            if not isinstance(data, dict):
                continue

            if event == "user_message":
                text = str(data.get("text") or "").strip()
                if len(text) < 3:
                    continue
                chat_store.append_message(sid, role="user", text=text)
                # Echo so other tabs / snapshot consumers see the turn.
                chat_store.publish(
                    sid,
                    "user_message",
                    {"session_id": sid, "text": text},
                )
                # Cancel any prior generation.
                prior = chat_store.get_generation(sid)
                if prior is not None:
                    prior.request_cancel()
                handle = chat_store.begin_generation(sid)
                gen_task = asyncio.create_task(
                    asyncio.to_thread(
                        _run_generation_sync,
                        session_id=sid,
                        question=text,
                        handle_message_id=handle.message_id,
                    )
                )

            elif event == "interrupt_requested":
                new_input = str(data.get("new_input") or "").strip()
                handle = chat_store.get_generation(sid)
                if handle is not None:
                    handle.request_cancel()
                # Wait briefly for interrupt event to flush.
                if gen_task is not None and not gen_task.done():
                    try:
                        await asyncio.wait_for(asyncio.shield(gen_task), timeout=15.0)
                    except (TimeoutError, Exception):  # noqa: BLE001
                        pass
                if new_input:
                    chat_store.append_message(sid, role="user", text=new_input)
                    chat_store.publish(
                        sid,
                        "user_message",
                        {"session_id": sid, "text": new_input},
                    )
                    handle = chat_store.begin_generation(sid)
                    gen_task = asyncio.create_task(
                        asyncio.to_thread(
                            _run_generation_sync,
                            session_id=sid,
                            question=new_input,
                            handle_message_id=handle.message_id,
                        )
                    )

    except WebSocketDisconnect:
        logger.info("compliance chat disconnected session_id=%s", sid)
    finally:
        stop_pump.set()
        handle = chat_store.get_generation(sid)
        if handle is not None:
            handle.request_cancel()
        chat_store.unsubscribe(sid, queue)
        pump_task.cancel()
        try:
            await pump_task
        except asyncio.CancelledError:
            pass
