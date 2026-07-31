import re
from .models import Incident

VALID_CLINICS = {
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

VALID_CATEGORIES = {
    "APPOINTMENT",
    "BILLING",
    "CLINICAL_CARE",
    "ACCESSIBILITY",
    "ADMINISTRATIVE",
}

def _first_failure_reason(incident: Incident) -> str | None:
    clinic = (incident.clinic_id or "").strip()
    if not clinic or clinic not in VALID_CLINICS:
        return "invalid_clinic_id"

    if incident.country.strip() != VALID_CLINICS[clinic]:
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

    if incident.satisfaction_score is not None and incident.satisfaction_score not in range(1, 6):
        return "score_out_of_range"

    return None
    ...

def validate_incidents(
    incidents: list[Incident],
) -> tuple[list[Incident], dict[str, int]]:
    valid: list[Incident] = []
    counts = {
        "invalid_clinic_id": 0,
        "country_clinic_mismatch": 0,
        "invalid_category": 0,
        "empty_description": 0,
        "missing_patient_id": 0,
        "closed_without_score": 0,
        "score_out_of_range": 0,
    }

    for incident in incidents:
        reason = _first_failure_reason(incident)
        if reason is None:
            valid.append(incident)
        else:
            counts[reason] += 1

    return valid, counts

