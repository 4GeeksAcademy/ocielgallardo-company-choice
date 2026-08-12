"""Incident HTTP endpoints: CSV analysis plus centralized manager CRUD."""

import csv

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from services.app.core.deps import get_current_user
from services.app.domain.incident_manager_service import (
    IncidentNotFoundError,
    IncidentValidationError,
    create_incident,
    get_incident,
    get_incident_summary,
    list_incidents,
    update_incident_status,
)
from services.app.domain.incident_service import analyze_csv_bytes, results_csv_path
from services.app.models.incident import (
    Incident,
    IncidentCreate,
    IncidentStatusUpdate,
    IncidentSummary,
)
from services.app.models.user import UserPublic

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def _validation_http_exception(exc: IncidentValidationError) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=[error.as_dict() for error in exc.errors],
    )


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    _current_user: UserPublic = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")

    try:
        content = await file.read()
    except OSError:
        raise HTTPException(
            status_code=400,
            detail="Could not read the uploaded file.",
        ) from None

    try:
        return analyze_csv_bytes(content)
    except (UnicodeDecodeError, csv.Error, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or malformed CSV file.",
        ) from exc
    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Could not process the CSV file. Please try again later.",
        ) from None


@router.get("/results/export")
async def export_last_results(
    _current_user: UserPublic = Depends(get_current_user),
):
    results_csv = results_csv_path()
    if not results_csv.exists():
        raise HTTPException(
            status_code=404,
            detail="No analysis results available. Run POST /api/incidents/analyze first.",
        )
    return FileResponse(
        path=results_csv,
        media_type="text/csv",
        filename="results.csv",
    )


@router.get("/summary", response_model=IncidentSummary)
def incidents_summary(
    _current_user: UserPublic = Depends(get_current_user),
):
    """Return aggregated metrics; zeros when the store is empty."""
    return get_incident_summary()


@router.post("", response_model=Incident, status_code=201)
def create_incident_endpoint(
    payload: IncidentCreate,
    _current_user: UserPublic = Depends(get_current_user),
):
    """Register a new incident with field-level validation."""
    try:
        return create_incident(payload)
    except IncidentValidationError as exc:
        raise _validation_http_exception(exc) from exc


@router.get("", response_model=list[Incident])
def list_incidents_endpoint(
    status: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    branch: str | None = Query(default=None),
    category: str | None = Query(default=None),
    _current_user: UserPublic = Depends(get_current_user),
):
    """List incidents with optional filters."""
    return list_incidents(
        status=status,
        origin=origin,
        branch=branch,
        category=category,
    )


@router.get("/{incident_id}", response_model=Incident)
def get_incident_endpoint(
    incident_id: int,
    _current_user: UserPublic = Depends(get_current_user),
):
    """Return one incident or 404."""
    try:
        return get_incident(incident_id)
    except IncidentNotFoundError:
        raise HTTPException(status_code=404, detail="Incident not found")


@router.patch("/{incident_id}/status", response_model=Incident)
def patch_incident_status_endpoint(
    incident_id: int,
    payload: IncidentStatusUpdate,
    _current_user: UserPublic = Depends(get_current_user),
):
    """Update incident status when the lifecycle transition is allowed."""
    try:
        return update_incident_status(incident_id, payload)
    except IncidentNotFoundError:
        raise HTTPException(status_code=404, detail="Incident not found")
    except IncidentValidationError as exc:
        raise _validation_http_exception(exc) from exc
