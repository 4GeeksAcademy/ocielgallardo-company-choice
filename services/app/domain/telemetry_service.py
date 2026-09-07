"""Domain logic for HealthCore telemetry ingest (validate + bulk persist)."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session

from services.app.models.telemetry import TelemetryEventRow
from services.app.schemas import TelemetryEvent, TelemetryIngestResponse

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMAS_PATH = _REPO_ROOT / "docs" / "telemetry" / "event-schemas.json"
DEFAULT_SERVICE = "backoffice"


@lru_cache(maxsize=1)
def _load_allowlists() -> dict[str, frozenset[str]]:
    """Map event_type → property allowlist from event-schemas.json `$defs`."""
    raw = json.loads(_SCHEMAS_PATH.read_text(encoding="utf-8"))
    allowlists: dict[str, frozenset[str]] = {}
    for key, value in raw.get("$defs", {}).items():
        if isinstance(value, dict) and "x-allowlist" in value:
            allowlists[key] = frozenset(value["x-allowlist"])
    return allowlists


def filter_tags(event_type: str, properties: dict[str, object]) -> dict[str, Any]:
    """Keep only allowlisted property keys for the given event_type."""
    allowed = _load_allowlists().get(event_type)
    if allowed is None:
        return {}
    return {k: v for k, v in properties.items() if k in allowed}


def ingest_events(
    session: Session, raw_events: list[dict[str, object]]
) -> TelemetryIngestResponse:
    """Validate each event independently; bulk-insert valid rows in one commit."""
    received = len(raw_events)
    rejected = 0
    rows: list[dict[str, Any]] = []

    for raw in raw_events:
        try:
            event = TelemetryEvent.model_validate(raw)
        except ValidationError:
            rejected += 1
            continue

        rows.append(
            {
                "event_id": event.eventId,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "service": DEFAULT_SERVICE,
                "user_id": event.userId,
                "session_id": event.sessionId,
                "tags": filter_tags(event.event_type, event.properties),
            }
        )

    stored = 0
    if rows:
        session.execute(pg_insert(TelemetryEventRow), rows)
        session.commit()
        stored = len(rows)
        logger.info(
            "telemetry stored %s events (rejected %s of %s): %s",
            stored,
            rejected,
            received,
            [r["event_type"] for r in rows],
        )
    else:
        logger.info(
            "telemetry received %s events, stored 0, rejected %s",
            received,
            rejected,
        )

    return TelemetryIngestResponse(
        received=received, stored=stored, rejected=rejected
    )
