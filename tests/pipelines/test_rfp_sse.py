"""Tests for RFP SSE payload + publish hook on valid intake only."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from data.pipelines.rfp_intake.graph import discard_node, orchestrate_node
from services.app.domain.rfp_sse import (
    RFP_TICKET_CREATED_EVENT,
    build_rfp_ticket_created_payload,
    format_sse_message,
    provisional_rfp_id,
    publish_rfp_ticket_created,
)

FIXTURES = Path(__file__).parent / "fixtures" / "rfp_intake"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_build_payload_uses_briefing_fields_only() -> None:
    payload = build_rfp_ticket_created_payload(
        ticket_id="abcd1234-5678-90ab-cdef-111111111111",
        metadata={
            "client_name": "Westbrook Manufacturing",
            "client_country": "US",
            "program_type": "occupational_health",
            "covered_population": "employees",
            "contains_phi": True,
            "patient_name": "SHOULD_NOT_APPEAR",
        },
        status="analyzing",
        created_at="2026-07-24T14:32:00Z",
    )
    assert payload["ticket_id"].startswith("abcd1234")
    assert payload["rfp_id"] == provisional_rfp_id(payload["ticket_id"])
    assert payload["client_name"] == "Westbrook Manufacturing"
    assert payload["client_country"] == "US"
    assert payload["program_type"] == "occupational_health"
    assert payload["status"] == "analyzing"
    assert payload["created_at"] == "2026-07-24T14:32:00Z"
    assert "patient_name" not in payload
    assert "contains_phi" not in payload
    assert "covered_population" not in payload


def test_format_sse_message_is_flat_event_data() -> None:
    frame = format_sse_message(
        event=RFP_TICKET_CREATED_EVENT,
        data={
            "ticket_id": "tkt_0508",
            "rfp_id": "rfp_0193",
            "status": "analyzing",
        },
    )
    assert frame.startswith("event: rfp_ticket_created\n")
    assert 'data: {"ticket_id": "tkt_0508"' in frame or 'data: {"ticket_id":"tkt_0508"' in frame.replace(
        " ", ""
    )
    assert '"event"' not in frame.split("data:", 1)[1]
    assert frame.endswith("\n\n")


def test_publish_soft_fails_without_redis(monkeypatch) -> None:
    def _boom(*_a, **_k):
        raise ConnectionError("redis down")

    monkeypatch.setattr(
        "redis.Redis.from_url",
        _boom,
        raising=False,
    )
    # Force import path used inside publish
    import redis as redis_mod

    monkeypatch.setattr(
        redis_mod.Redis,
        "from_url",
        classmethod(lambda *_a, **_k: (_ for _ in ()).throw(ConnectionError("down"))),
    )
    ok = publish_rfp_ticket_created(
        build_rfp_ticket_created_payload(ticket_id="ticket-1")
    )
    assert ok is False


def test_publish_calls_redis_channel(monkeypatch) -> None:
    published: list[tuple[str, str]] = []
    client = MagicMock()
    client.publish.side_effect = lambda channel, message: published.append(
        (channel, message)
    )

    import redis as redis_mod

    monkeypatch.setattr(
        redis_mod.Redis,
        "from_url",
        classmethod(lambda *_a, **_k: client),
    )

    payload = build_rfp_ticket_created_payload(
        ticket_id="ticket-publish-1",
        metadata={"client_name": "Acme"},
    )
    assert publish_rfp_ticket_created(payload) is True
    assert len(published) == 1
    channel, message = published[0]
    assert channel == "healthcore:rfp:events"
    assert "rfp_ticket_created" in message
    assert "ticket-publish-1" in message
    client.close.assert_called()


def test_orchestrate_publishes_ticket_created(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        "services.app.domain.rfp_sse.publish_rfp_ticket_created",
        lambda payload: calls.append(payload) or True,
    )
    # orchestrate_node imports publish lazily from the module — patch at source
    import services.app.domain.rfp_sse as sse_mod

    monkeypatch.setattr(
        sse_mod,
        "publish_rfp_ticket_created",
        lambda payload: calls.append(payload) or True,
    )

    result = orchestrate_node(
        {
            "ticket_id": "orch-ticket-001",
            "markdown": _load("formal_meridian.md"),
            "contains_phi": False,
        }
    )
    assert "metadata" in result
    assert len(calls) == 1
    assert calls[0]["ticket_id"] == "orch-ticket-001"
    assert calls[0]["status"] == "analyzing"


def test_discard_path_does_not_publish(monkeypatch) -> None:
    calls: list[dict] = []
    import services.app.domain.rfp_sse as sse_mod

    monkeypatch.setattr(
        sse_mod,
        "publish_rfp_ticket_created",
        lambda payload: calls.append(payload) or True,
    )
    out = discard_node(
        {
            "ticket_id": "discard-me",
            "discard_reason": "Not a valid institutional RFP",
            "classification": {"is_rfp": False, "reason": "vendor pitch"},
        }
    )
    assert out["status"] == "discarded"
    assert calls == []
