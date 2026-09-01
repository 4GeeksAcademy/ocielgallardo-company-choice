"""Pydantic models for the HealthCore centralized incident manager."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class IncidentCategory(str, Enum):
    CLINICAL_EQUIPMENT = "clinical_equipment"
    IT_SYSTEM = "it_system"
    BILLING_ERROR = "billing_error"
    COMPLIANCE_BREACH = "compliance_breach"
    PATIENT_EXPERIENCE = "patient_experience"
    STAFF_ISSUE = "staff_issue"
    FACILITY_ISSUE = "facility_issue"
    REFERRAL_ISSUE = "referral_issue"
    OTHER = "other"


class IncidentStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISCARDED = "discarded"


class IncidentOrigin(str, Enum):
    CUSTOMER = "customer"
    BRANCH = "branch"
    INTERNAL = "internal"


class IncidentBranch(str, Enum):
    CENTRAL = "central"
    AUSTIN_NORTH = "austin_north"
    DALLAS_UPTOWN = "dallas_uptown"
    HOUSTON_MED_CENTER = "houston_med_center"
    SAN_ANTONIO_WEST = "san_antonio_west"
    MIAMI_BRICKELL = "miami_brickell"
    MIAMI_DORAL = "miami_doral"
    ORLANDO_EAST = "orlando_east"
    TAMPA_BAY = "tampa_bay"
    ATLANTA_MIDTOWN = "atlanta_midtown"
    SAVANNAH = "savannah"
    LONDON_CITY = "london_city"
    LONDON_WEST = "london_west"
    MANCHESTER_CENTRAL = "manchester_central"


class IncidentCreate(BaseModel):
    """Payload to register a new incident."""

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: IncidentCategory
    origin: IncidentOrigin
    branch: IncidentBranch
    status: IncidentStatus = IncidentStatus.OPEN


class IncidentStatusUpdate(BaseModel):
    """Payload to update only the incident lifecycle status."""

    status: IncidentStatus


class IncidentListItem(BaseModel):
    """Lean row for GET /api/incidents list (backoffice table columns)."""

    id: int
    title: str
    description: str
    category: IncidentCategory
    status: IncidentStatus
    origin: IncidentOrigin
    branch: IncidentBranch


class Incident(IncidentListItem):
    """Full incident returned by detail and write confirmations."""

    created_at: datetime | str
    updated_at: datetime | str


class IncidentSummary(BaseModel):
    """Aggregated incident metrics (manager store)."""

    by_status: dict[str, int]
    by_category: dict[str, int]
    by_origin: dict[str, int]
    by_branch: dict[str, int]
    total: int


# --- CSV analysis summary (POST /api/incidents/analyze) ---
# Must never include patient_id or other PHI.


class CountPercentage(BaseModel):
    count: int
    percentage: float


class SatisfactionSummary(BaseModel):
    scored_cases: int
    average: float | None
    histogram: dict[int, int]


class IncidentAnalysisSummary(BaseModel):
    """Aggregate-only CSV analysis result. No row-level or patient fields."""

    total: int
    valid: int
    invalid: int
    invalid_breakdown: dict[str, int]
    by_category: dict[str, CountPercentage]
    by_status: dict[str, CountPercentage]
    by_country: dict[str, CountPercentage]
    satisfaction: SatisfactionSummary
