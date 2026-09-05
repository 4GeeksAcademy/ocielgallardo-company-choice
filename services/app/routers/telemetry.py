"""Telemetry ingest endpoint — validates per event and bulk-persists to Supabase."""

from collections.abc import Generator
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from services.app.core.database import get_engine, is_inventory_db_configured
from services.app.domain import telemetry_service
from services.app.schemas import TelemetryBatch, TelemetryIngestResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def get_telemetry_db() -> Generator[Session, None, None]:
    """Yield a DB session, or 503 when Supabase is not configured."""
    if not is_inventory_db_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telemetry storage requires DATABASE_URL or SUPABASE_DB_* in .env",
        )
    with Session(get_engine()) as session:
        yield session


@router.post("/events", response_model=TelemetryIngestResponse)
def ingest_telemetry_events(
    batch: TelemetryBatch,
    session: Session = Depends(get_telemetry_db),
) -> TelemetryIngestResponse:
    """Accept a loose {events: [...]} envelope; persist valid items only."""
    return telemetry_service.ingest_events(session, batch.events)
