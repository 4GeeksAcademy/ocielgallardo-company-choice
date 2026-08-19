"""Incident manager enums, labels, and status lifecycle for HealthCore."""

from __future__ import annotations

MANAGER_BRANCHES: frozenset[str] = frozenset(
    {
        "central",
        "austin_north",
        "dallas_uptown",
        "houston_med_center",
        "san_antonio_west",
        "miami_brickell",
        "miami_doral",
        "orlando_east",
        "tampa_bay",
        "atlanta_midtown",
        "savannah",
        "london_city",
        "london_west",
        "manchester_central",
    }
)

BRANCH_DISPLAY_LABELS: dict[str, str] = {
    "central": "Central — Austin Main Clinic",
    "austin_north": "Austin — North",
    "dallas_uptown": "Dallas Uptown",
    "houston_med_center": "Houston Medical Center",
    "san_antonio_west": "San Antonio West",
    "miami_brickell": "Miami Brickell",
    "miami_doral": "Miami Doral",
    "orlando_east": "Orlando East",
    "tampa_bay": "Tampa Bay",
    "atlanta_midtown": "Atlanta Midtown",
    "savannah": "Savannah",
    "london_city": "London City",
    "london_west": "London West End",
    "manchester_central": "Manchester Central",
}

MANAGER_CATEGORIES: frozenset[str] = frozenset(
    {
        "clinical_equipment",
        "it_system",
        "billing_error",
        "compliance_breach",
        "patient_experience",
        "staff_issue",
        "facility_issue",
        "referral_issue",
        "other",
    }
)

MANAGER_STATUSES: frozenset[str] = frozenset(
    {"open", "in_progress", "resolved", "discarded"}
)

MANAGER_ORIGINS: frozenset[str] = frozenset({"customer", "branch", "internal"})

ALLOWED_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"in_progress", "discarded"}),
    "in_progress": frozenset({"resolved", "discarded"}),
    "resolved": frozenset(),
    "discarded": frozenset(),
}


def is_allowed_status_transition(current: str, new_status: str) -> bool:
    """Return True when new_status is a valid next lifecycle state."""
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current, frozenset())
    return new_status in allowed
