"""Incident manager business logic (TinyDB persistence)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from tinydb import Query

from healthcore_shared.manager_constants import (
    MANAGER_BRANCHES,
    MANAGER_CATEGORIES,
    MANAGER_ORIGINS,
    MANAGER_STATUSES,
)
from healthcore_shared.manager_validation import (
    FieldError,
    validate_incident_create,
    validate_status_transition,
)
from healthcore_shared.seed_mapping import SeedIncidentDraft
from services.app.core.database import incidents_table
from services.app.models.incident import (
    Incident,
    IncidentCreate,
    IncidentStatusUpdate,
    IncidentSummary,
)


class IncidentNotFoundError(LookupError):
    """Raised when an incident id does not exist in TinyDB."""


class IncidentValidationError(ValueError):
    """Raised when create/status payload fails field validation."""

    def __init__(self, errors: list[FieldError]):
        self.errors = errors
        super().__init__("Incident validation failed")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _doc_to_response(doc) -> Incident:
    return Incident(
        id=doc.doc_id,
        title=doc["title"],
        description=doc["description"],
        category=doc["category"],
        status=doc["status"],
        origin=doc["origin"],
        branch=doc["branch"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def create_incident(payload: IncidentCreate) -> Incident:
    """Create a new incident after shared field validation."""
    raw = {
        "title": payload.title,
        "description": payload.description,
        "category": payload.category.value,
        "origin": payload.origin.value,
        "branch": payload.branch.value,
        "status": payload.status.value,
    }
    errors = validate_incident_create(raw)
    if errors:
        raise IncidentValidationError(errors)

    now = _now_iso()
    doc = {
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "category": payload.category.value,
        "status": payload.status.value,
        "origin": payload.origin.value,
        "branch": payload.branch.value,
        "created_at": now,
        "updated_at": now,
        "source_incident_id": None,
    }
    doc_id = incidents_table.insert(doc)
    stored = incidents_table.get(doc_id=doc_id)
    return _doc_to_response(stored)


def list_incidents(
    status: str | None = None,
    origin: str | None = None,
    branch: str | None = None,
    category: str | None = None,
) -> list[Incident]:
    """List incidents with optional exact-match filters."""
    results = incidents_table.all()

    if status:
        results = [r for r in results if r.get("status") == status]
    if origin:
        results = [r for r in results if r.get("origin") == origin]
    if branch:
        results = [r for r in results if r.get("branch") == branch]
    if category:
        results = [r for r in results if r.get("category") == category]

    return [_doc_to_response(r) for r in results]


def get_incident(incident_id: int) -> Incident:
    """Get a single incident by TinyDB document id."""
    doc = incidents_table.get(doc_id=incident_id)
    if doc is None:
        raise IncidentNotFoundError("Incident not found")
    return _doc_to_response(doc)


def update_incident_status(
    incident_id: int, payload: IncidentStatusUpdate
) -> Incident:
    """Update status when the lifecycle transition is allowed."""
    doc = incidents_table.get(doc_id=incident_id)
    if doc is None:
        raise IncidentNotFoundError("Incident not found")

    current = doc.get("status", "open")
    new_status = payload.status.value
    error = validate_status_transition(current, new_status)
    if error:
        raise IncidentValidationError([error])

    incidents_table.update(
        {"status": new_status, "updated_at": _now_iso()},
        doc_ids=[incident_id],
    )
    updated = incidents_table.get(doc_id=incident_id)
    return _doc_to_response(updated)


def _zero_counts(keys: frozenset[str]) -> dict[str, int]:
    return {key: 0 for key in sorted(keys)}


def get_incident_summary() -> IncidentSummary:
    """Aggregate counts by status, category, origin, and branch."""
    rows = incidents_table.all()
    by_status = _zero_counts(MANAGER_STATUSES)
    by_category = _zero_counts(MANAGER_CATEGORIES)
    by_origin = _zero_counts(MANAGER_ORIGINS)
    by_branch = _zero_counts(MANAGER_BRANCHES)

    status_counts = Counter(r.get("status") for r in rows if r.get("status"))
    category_counts = Counter(r.get("category") for r in rows if r.get("category"))
    origin_counts = Counter(r.get("origin") for r in rows if r.get("origin"))
    branch_counts = Counter(r.get("branch") for r in rows if r.get("branch"))

    for key, value in status_counts.items():
        if key in by_status:
            by_status[key] = value
    for key, value in category_counts.items():
        if key in by_category:
            by_category[key] = value
    for key, value in origin_counts.items():
        if key in by_origin:
            by_origin[key] = value
    for key, value in branch_counts.items():
        if key in by_branch:
            by_branch[key] = value

    return IncidentSummary(
        by_status=by_status,
        by_category=by_category,
        by_origin=by_origin,
        by_branch=by_branch,
        total=len(rows),
    )


def source_incident_exists(source_incident_id: str) -> bool:
    """Return True if a seed row with this CSV id was already inserted."""
    IncidentQ = Query()
    return (
        incidents_table.get(IncidentQ.source_incident_id == source_incident_id)
        is not None
    )


def insert_seed_incident(draft: SeedIncidentDraft) -> int | None:
    """Insert a mapped seed draft if not already present. Returns new id or None."""
    if source_incident_exists(draft.source_incident_id):
        return None

    doc = {
        "title": draft.title,
        "description": draft.description,
        "category": draft.category,
        "status": draft.status,
        "origin": draft.origin,
        "branch": draft.branch,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
        "source_incident_id": draft.source_incident_id,
    }
    return incidents_table.insert(doc)
