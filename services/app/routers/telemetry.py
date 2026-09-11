"""Telemetry ingest + operational report endpoints."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from services.app.core.database import get_engine, is_inventory_db_configured
from services.app.core.ttl_cache import telemetry_report_cache
from services.app.domain import telemetry_service
from services.app.schemas import (
    TelemetryBatch,
    TelemetryIngestResponse,
    TelemetryReportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

REPORT_CACHE_TTL_SECONDS = 60


def get_telemetry_db() -> Generator[Session, None, None]:
    """Yield a DB session, or 503 when Supabase is not configured."""
    if not is_inventory_db_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telemetry storage requires DATABASE_URL or SUPABASE_DB_* in .env",
        )
    with Session(get_engine()) as session:
        yield session


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _resolve_report_period(
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[datetime, datetime]:
    """Default to last 7 days UTC when params omitted; start inclusive, end exclusive."""
    end = _as_utc(end_date) if end_date is not None else datetime.now(timezone.utc)
    start = (
        _as_utc(start_date)
        if start_date is not None
        else end - timedelta(days=7)
    )
    if start >= end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be strictly before end_date",
        )
    return start, end


@router.post("/events", response_model=TelemetryIngestResponse)
def ingest_telemetry_events(
    batch: TelemetryBatch,
    session: Session = Depends(get_telemetry_db),
) -> TelemetryIngestResponse:
    """Accept a loose {events: [...]} envelope; persist valid items only."""
    return telemetry_service.ingest_events(session, batch.events)


@router.get("/report", response_model=TelemetryReportResponse)
def get_telemetry_report(
    start_date: datetime | None = Query(
        default=None,
        description="ISO 8601 inclusive start (UTC). Defaults to end_date - 7 days.",
    ),
    end_date: datetime | None = Query(
        default=None,
        description="ISO 8601 exclusive end (UTC). Defaults to now.",
    ),
    session: Session = Depends(get_telemetry_db),
) -> TelemetryReportResponse:
    """Serve cached operational metrics for a resolved period (TTL 60s)."""
    start, end = _resolve_report_period(start_date, end_date)
    cache_key = f"{start.isoformat()}|{end.isoformat()}"

    cached = telemetry_report_cache.get(cache_key)
    if cached is not None:
        return TelemetryReportResponse.model_validate(cached)

    try:
        from services.app.domain.telemetry_analysis import build_report
    except ModuleNotFoundError as exc:
        logger.exception("Telemetry report unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telemetry report requires pandas. Rebuild the backend image.",
        ) from exc

    report = build_report(session.get_bind(), start, end)
    telemetry_report_cache.set(cache_key, report, REPORT_CACHE_TTL_SECONDS)
    return TelemetryReportResponse.model_validate(report)
