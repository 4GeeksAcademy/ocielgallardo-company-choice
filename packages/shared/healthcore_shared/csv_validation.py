"""CSV incident validation rules shared by the analyzer CLI/API and seed script."""

from __future__ import annotations

import re
from typing import Any, Protocol


class CsvIncidentLike(Protocol):
    """Minimal CSV incident shape used by validation."""

    clinic_id: str
    country: str
    category: str
    description: str
    status: str
    patient_id: str
    satisfaction_score: int | None


VALID_CLINICS: dict[str, str] = {
    "US-TX-01": "US",
    "US-TX-02": "US",
    "US-TX-03": "US",
    "US-FL-01": "US",
    "US-FL-02": "US",
    "US-FL-03": "US",
    "US-GA-01": "US",
    "US-GA-02": "US",
    "US-GA-03": "US",
    "UK-LON-01": "UK",
    "UK-LON-02": "UK",
    "UK-MAN-01": "UK",
}

VALID_CATEGORIES: set[str] = {
    "APPOINTMENT",
    "BILLING",
    "CLINICAL_CARE",
    "ACCESSIBILITY",
    "ADMINISTRATIVE",
}

INVALID_REASON_KEYS: tuple[str, ...] = (
    "invalid_clinic_id",
    "country_clinic_mismatch",
    "invalid_category",
    "empty_description",
    "missing_patient_id",
    "closed_without_score",
    "score_out_of_range",
)


def first_failure_reason(incident: CsvIncidentLike) -> str | None:
    """Return the first CONTEXT invalidity reason, or None if the row is valid."""
    clinic = (incident.clinic_id or "").strip()
    if not clinic or clinic not in VALID_CLINICS:
        return "invalid_clinic_id"

    if (incident.country or "").strip() != VALID_CLINICS[clinic]:
        return "country_clinic_mismatch"

    if (incident.category or "").strip() not in VALID_CATEGORIES:
        return "invalid_category"

    if len((incident.description or "").strip()) < 5:
        return "empty_description"

    patient_id = (incident.patient_id or "").strip()
    if not re.fullmatch(r"PAT-\d{6}", patient_id):
        return "missing_patient_id"

    if incident.status == "CLOSED" and incident.satisfaction_score is None:
        return "closed_without_score"

    if incident.satisfaction_score is not None and incident.satisfaction_score not in range(
        1, 6
    ):
        return "score_out_of_range"

    return None


def validate_incidents(
    incidents: list[Any],
) -> tuple[list[Any], dict[str, int]]:
    """Split CSV incidents into valid rows and invalid-reason counts."""
    valid: list[Any] = []
    counts = {key: 0 for key in INVALID_REASON_KEYS}

    for incident in incidents:
        reason = first_failure_reason(incident)
        if reason is None:
            valid.append(incident)
        else:
            counts[reason] += 1

    return valid, counts
