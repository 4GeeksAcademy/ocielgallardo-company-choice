"""RFP ticket SSE fan-out over Redis pub/sub (API subscribers ↔ Celery publishers)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

RFP_SSE_CHANNEL = "healthcore:rfp:events"
RFP_TICKET_CREATED_EVENT = "rfp_ticket_created"

# Allowed keys for rfp_ticket_created — never PHI / patient fields.
_TICKET_CREATED_KEYS = (
    "ticket_id",
    "rfp_id",
    "client_name",
    "client_country",
    "program_type",
    "status",
    "created_at",
)


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def provisional_rfp_id(ticket_id: str) -> str:
    """Same formula as intake completion; safe to advertise while still analyzing."""
    return f"rfp-{ticket_id[:8]}"


def build_rfp_ticket_created_payload(
    *,
    ticket_id: str,
    metadata: dict[str, Any] | None = None,
    status: str = "analyzing",
    created_at: str | datetime | None = None,
    rfp_id: str | None = None,
) -> dict[str, Any]:
    """Build a PHI-safe notification payload (flat dict for SSE data:)."""
    meta = metadata or {}
    if isinstance(created_at, datetime):
        created_at_str = created_at.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
    elif created_at:
        created_at_str = str(created_at)
    else:
        created_at_str = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

    payload: dict[str, Any] = {
        "ticket_id": ticket_id,
        "rfp_id": rfp_id or provisional_rfp_id(ticket_id),
        "client_name": meta.get("client_name"),
        "client_country": meta.get("client_country"),
        "program_type": meta.get("program_type"),
        "status": status,
        "created_at": created_at_str,
    }
    return {k: payload.get(k) for k in _TICKET_CREATED_KEYS}


def format_sse_message(*, event: str, data: dict[str, Any]) -> str:
    """SSE frame: event: line + data: JSON (not a nested event/data envelope)."""
    body = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {body}\n\n"


def publish_rfp_ticket_created(payload: dict[str, Any]) -> bool:
    """Publish to Redis. Soft-fails so intake never crashes on notify errors."""
    safe = {k: payload.get(k) for k in _TICKET_CREATED_KEYS}
    if not safe.get("ticket_id"):
        logger.warning("rfp_sse: refused publish without ticket_id")
        return False
    message = json.dumps(
        {"event": RFP_TICKET_CREATED_EVENT, "data": safe},
        ensure_ascii=False,
        default=str,
    )
    try:
        import redis

        client = redis.Redis.from_url(_redis_url(), decode_responses=True)
        client.publish(RFP_SSE_CHANNEL, message)
        client.close()
        return True
    except Exception:  # noqa: BLE001 — notify must not break intake
        logger.exception("rfp_sse: publish failed channel=%s", RFP_SSE_CHANNEL)
        return False


async def iter_rfp_sse_events(
    *,
    heartbeat_seconds: float = 15.0,
) -> AsyncIterator[str]:
    """Async generator yielding SSE frames from Redis + periodic heartbeats."""
    import asyncio

    import redis.asyncio as aioredis

    client = aioredis.from_url(_redis_url(), decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(RFP_SSE_CHANNEL)
    try:
        yield ": connected\n\n"
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    ),
                    timeout=heartbeat_seconds,
                )
            except TimeoutError:
                yield ": ping\n\n"
                continue

            if message is None:
                continue
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if not isinstance(raw, str):
                continue
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("rfp_sse: bad redis payload")
                continue
            event = envelope.get("event") or RFP_TICKET_CREATED_EVENT
            data = envelope.get("data")
            if not isinstance(data, dict):
                continue
            safe = {k: data.get(k) for k in _TICKET_CREATED_KEYS}
            yield format_sse_message(event=event, data=safe)
    finally:
        try:
            await pubsub.unsubscribe(RFP_SSE_CHANNEL)
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            logger.debug("rfp_sse: pubsub close error", exc_info=True)
        try:
            await client.aclose()
        except Exception:  # noqa: BLE001
            logger.debug("rfp_sse: redis close error", exc_info=True)
