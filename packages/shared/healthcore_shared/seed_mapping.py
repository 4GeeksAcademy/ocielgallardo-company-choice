"""Map analyzer CSV rows to incident-manager records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from healthcore_shared.manager_constants import MANAGER_BRANCHES

CSV_STATUS_TO_MANAGER: dict[str, str] = {
    "OPEN": "open",
    "CLOSED": "resolved",
    "DISCARDED": "discarded",
}

CSV_CATEGORY_TO_MANAGER: dict[str, str] = {
    "APPOINTMENT": "patient_experience",
    "BILLING": "billing_error",
    "CLINICAL_CARE": "patient_experience",
    "ACCESSIBILITY": "patient_experience",
    "ADMINISTRATIVE": "other",
}

CLINIC_ID_TO_BRANCH: dict[str, str] = {
    "US-TX-01": "central",
    "US-TX-02": "austin_north",
    "US-TX-03": "houston_med_center",
    "US-FL-01": "miami_brickell",
    "US-FL-02": "orlando_east",
    "US-FL-03": "tampa_bay",
    "US-GA-01": "atlanta_midtown",
    "US-GA-02": "atlanta_midtown",
    "US-GA-03": "savannah",
    "UK-LON-01": "london_city",
    "UK-LON-02": "london_west",
    "UK-MAN-01": "manchester_central",
}


@dataclass(frozen=True)
class SeedIncidentDraft:
    """Normalized manager incident ready for TinyDB insert."""

    source_incident_id: str
    title: str
    description: str
    category: str
    status: str
    origin: str
    branch: str
    created_at: str
    updated_at: str


def _parse_csv_date_to_utc_iso(date_str: str) -> str | None:
    raw = (date_str or "").strip()
    try:
        day = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return day.isoformat().replace("+00:00", "Z")


def map_csv_incident_to_manager(incident: Any) -> SeedIncidentDraft | None:
    """Transform a validated CSV incident into a manager draft, or None if unmappable."""
    description = (getattr(incident, "description", None) or "").strip()
    title = description[:120].strip()
    if not title:
        return None

    csv_status = (getattr(incident, "status", None) or "").strip()
    status = CSV_STATUS_TO_MANAGER.get(csv_status)
    if status is None:
        return None

    csv_category = (getattr(incident, "category", None) or "").strip()
    category = CSV_CATEGORY_TO_MANAGER.get(csv_category)
    if category is None:
        return None

    clinic_id = (getattr(incident, "clinic_id", None) or "").strip()
    branch = CLINIC_ID_TO_BRANCH.get(clinic_id, "central")
    if branch not in MANAGER_BRANCHES:
        branch = "central"

    created_at = _parse_csv_date_to_utc_iso(getattr(incident, "date", "") or "")
    if created_at is None:
        return None

    source_id = (getattr(incident, "incident_id", None) or "").strip()
    if not source_id:
        source_id = f"{title}|{created_at}"

    return SeedIncidentDraft(
        source_incident_id=source_id,
        title=title,
        description=description,
        category=category,
        status=status,
        origin="customer",
        branch=branch,
        created_at=created_at,
        updated_at=created_at,
    )
