"""Incident HTTP endpoints: CSV analysis plus centralized manager CRUD."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from services.app.core.deps import get_current_user, require_scope
from services.app.core.service_identity import ServicePrincipal
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
    IncidentAnalysisSummary,
    IncidentCreate,
    IncidentListItem,
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


@router.post("/analyze", response_model=IncidentAnalysisSummary)
async def analyze(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")

    content = await file.read()
    return analyze_csv_bytes(content)


@router.get("/results/export")
async def export_last_results():
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
    _writer: UserPublic | ServicePrincipal = Depends(
        require_scope("incidents:write")
    ),
):
    """Register a new incident with field-level validation.

    Humans keep full access; service principals need the explicit
    ``incidents:write`` scope (MCP server identity). Service tokens without
    the scope get 403; every other service token stays rejected elsewhere
    (fail-closed, ``agent-graph.md`` §9.1).
    """
    try:
        return create_incident(payload)
    except IncidentValidationError as exc:
        raise _validation_http_exception(exc) from exc


@router.get("", response_model=list[IncidentListItem])
def list_incidents_endpoint(
    status: str | None = Query(default=None),
    origin: str | None = Query(default=None),
    branch: str | None = Query(default=None),
    category: str | None = Query(default=None),
    _reader: UserPublic | ServicePrincipal = Depends(
        require_scope("incidents:read")
    ),
):
    """List incidents with optional filters (lean list projection)."""
    return list_incidents(
        status=status,
        origin=origin,
        branch=branch,
        category=category,
    )


@router.get("/{incident_id}", response_model=Incident)
def get_incident_endpoint(
    incident_id: int,
    _reader: UserPublic | ServicePrincipal = Depends(
        require_scope("incidents:read")
    ),
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
    _writer: UserPublic | ServicePrincipal = Depends(
        require_scope("incidents:write")
    ),
):
    """Update incident status when the lifecycle transition is allowed.

    Same scope contract as ``POST /api/incidents`` (``incidents:write``).
    """
    try:
        return update_incident_status(incident_id, payload)
    except IncidentNotFoundError:
        raise HTTPException(status_code=404, detail="Incident not found")
    except IncidentValidationError as exc:
        raise _validation_http_exception(exc) from exc
