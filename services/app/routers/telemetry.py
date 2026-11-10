"""Telemetry ingest + operational report endpoints."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
import hmac
import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlmodel import Session

from services.app.core.database import get_engine, is_inventory_db_configured
from services.app.core.deps import get_current_user
from services.app.core.ttl_cache import telemetry_report_cache
from services.app.domain import telemetry_service
from services.app.models.user import UserPublic
from services.app.schemas import (
    TelemetryBatch,
    TelemetryIngestResponse,
    TelemetryReportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

REPORT_CACHE_TTL_SECONDS = 60


def require_telemetry_ingest_key(
    request: Request,
    x_telemetry_ingest_key: str | None = Header(default=None),
) -> None:
    """Require ``X-Telemetry-Ingest-Key`` when configured or in production."""
    expected = os.getenv("TELEMETRY_INGEST_KEY", "").strip()
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if expected:
        provided = (x_telemetry_ingest_key or "").strip()
        if not provided or not hmac.compare_digest(provided, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing telemetry ingest key",
            )
        return
    if app_env == "production":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TELEMETRY_INGEST_KEY must be set in production",
        )
    logger.warning(
        "TELEMETRY_INGEST_KEY unset; allowing ingest in non-prod (path=%s)",
        request.url.path,
    )


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
    _auth: None = Depends(require_telemetry_ingest_key),
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
    _current_user: UserPublic = Depends(get_current_user),
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
