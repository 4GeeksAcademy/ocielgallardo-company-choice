"""Temporary telemetry ingest stub. Validates envelope shape; does not persist."""

import logging
import os

from fastapi import APIRouter

from services.app.schemas import TelemetryBatch, TelemetryIngestResponse

logger = logging.getLogger(__name__)

TELEMETRY_ENDPOINT = os.getenv(
    "TELEMETRY_ENDPOINT",
    "http://localhost:8000/telemetry/events",
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events", response_model=TelemetryIngestResponse)
def ingest_telemetry_events(batch: TelemetryBatch) -> TelemetryIngestResponse:
    event_types = [event.event_type for event in batch.events]
    logger.info(
        "telemetry stub received %s events via %s: %s",
        len(batch.events),
        TELEMETRY_ENDPOINT,
        event_types,
    )
    return TelemetryIngestResponse(received=len(batch.events))