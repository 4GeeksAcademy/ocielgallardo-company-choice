"""Pydantic request/response schemas for HealthCore inventory API.

Kept separate from SQLModel ORM tables in ``models.inventory``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


SupplyCategory = Literal[
    "ppe",
    "wound_care",
    "diagnostics",
    "medications",
    "consumables",
]
SupplyUnit = Literal["box", "unit", "pack", "vial"]
SupplyCountry = Literal["US", "UK"]
ConsumptionType = Literal["clinical_use", "expiry_waste"]


class MedicalSupplyCreate(BaseModel):
    name: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    category: SupplyCategory
    unit: SupplyUnit
    country: SupplyCountry


class MedicalSupplyResponse(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str
    current_stock: int


class SupplyDeliveryCreate(BaseModel):
    supply_id: int
    quantity: int = Field(gt=0)
    vendor_name: str = Field(min_length=1)
    clinic_id: int = Field(ge=1, le=12)


class SupplyDeliveryResponse(BaseModel):
    id: int
    supply_id: int
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime
    user_uuid: str


class SupplyConsumptionCreate(BaseModel):
    supply_id: int
    quantity: int = Field(gt=0)
    consumption_type: ConsumptionType
    clinic_id: int = Field(ge=1, le=12)


class SupplyConsumptionResponse(BaseModel):
    id: int
    supply_id: int
    quantity: int
    consumption_type: str
    clinic_id: int
    created_at: datetime
    user_uuid: str


class InventoryOrderResponse(BaseModel):
    """Full unified order row (internal / write-adjacent projections)."""

    order_type: Literal["inbound", "outbound"]
    id: int
    supply_id: int
    supply_name: str
    supply_sku: str
    quantity: int
    clinic_id: int
    created_at: datetime
    user_uuid: str
    vendor_name: str | None = None
    consumption_type: str | None = None


class InventoryOrderListItem(BaseModel):
    """Lean history row for GET /inventory/orders (backoffice table columns)."""

    order_type: Literal["inbound", "outbound"]
    id: int
    supply_name: str
    quantity: int
    created_at: datetime
    user_uuid: str

class TelemetryEvent(BaseModel):
    """Standard event envelope from the HealthCore telemetry plan (Phase 1)."""

    eventId: str
    timestamp: datetime
    sessionId: str | None
    userId: str
    event_type: str
    schemaVersion: str
    requestId: str | None
    properties: dict[str, object]


class TelemetryBatch(BaseModel):
    """Loose envelope - events are raw dicts; validate per item in the handler."""

    events: list[dict[str, object]]


class TelemetryIngestResponse(BaseModel):
    received: int
    stored: int
    rejected: int


class TelemetryReportPeriod(BaseModel):
    """Inclusive start / exclusive end window resolved by the report endpoint."""

    model_config = {"populate_by_name": True, "serialize_by_alias": True}

    from_: str = Field(alias="from", serialization_alias="from")
    to: str


class TelemetryReportMetrics(BaseModel):
    events_per_day: list[dict[str, object]]
    error_rate_by_type: list[dict[str, object]]
    avg_latency_by_path: list[dict[str, object]]
    auth_failure_rate: list[dict[str, object]]


class TelemetryReportResponse(BaseModel):
    period: TelemetryReportPeriod
    metrics: TelemetryReportMetrics


class TaskStatusResponse(BaseModel):
    """Public status envelope for a Celery task."""

    task_id: str
    status: str
    result: object | None = None
    error: str | None = None


class RagQueryRequest(BaseModel):
    """Coordinator question for the knowledge assistant."""

    question: str = Field(min_length=3, max_length=1000)


class RagQueryResponse(BaseModel):
    """Model-generated answer only — never raw Qdrant chunks or scores."""

    question: str
    answer: str


# --- RFP intake / drafting (Milestone 9 Parts 1–2) ---


class ReadabilityEvalOut(BaseModel):
    pass_: bool = Field(default=False, alias="pass")
    score: Optional[float] = None
    details: str = ""

    model_config = {"populate_by_name": True}


class RelevanceEvalOut(BaseModel):
    pass_: bool = Field(default=False, alias="pass")
    missing_aspects: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ComplianceEvalOut(BaseModel):
    pass_: bool = Field(default=False, alias="pass")
    rule_ids: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class EvaluationResultOut(BaseModel):
    """Structured Part 2 evaluation (BRIEFING / ticket schema)."""

    section_id: str = ""
    department_id: str = ""
    readability: dict[str, Any] = Field(default_factory=dict)
    relevance: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    overall_pass: bool = False
    feedback_for_generator: str = ""
    contains_phi: bool = False


class DepartmentSectionOut(BaseModel):
    department_id: str
    owner: str
    key_aspects: list[Any] = Field(default_factory=list)
    open_questions: list[Any] = Field(default_factory=list)
    contains_phi: bool = False
    draft_content: Optional[str] = None
    evaluation_results: dict[str, Any] = Field(default_factory=dict)
    iteration_count: int = 0
    needs_human_review: bool = False
    approval_status: Optional[str] = None
    approver: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_round: int = 0


class RfpFinalDocumentOut(BaseModel):
    id: Optional[int] = None
    ticket_id: str
    sections: dict[str, Any] = Field(default_factory=dict)
    currency: str = "USD"
    generated_at: datetime
    content_markdown: str = ""


class RfpApprovalDecisionIn(BaseModel):
    decision: Literal["approved", "rejected", "request_changes"]
    note: Optional[str] = None


class RfpMetadataOut(BaseModel):
    client_name: Optional[str] = None
    client_country: Optional[str] = None
    program_type: Optional[str] = None
    covered_population: Optional[str] = None
    deadline: Optional[str] = None
    budget_range: Optional[str] = None
    departments_needed: list[Any] = Field(default_factory=list)
    flesch_kincaid_grade: Optional[float] = None
    gunning_fog: Optional[float] = None
    flesch_reading_ease: Optional[float] = None
    readability_metrics: dict[str, Any] = Field(default_factory=dict)
    contains_phi: bool = False
    original_filename: Optional[str] = None


class RfpTicketSummary(BaseModel):
    ticket_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    original_filename: Optional[str] = None
    client_name: Optional[str] = None
    ready_for_part2: bool = False
    ready_for_part3: bool = False


class RfpTicketDetail(BaseModel):
    ticket_id: str
    rfp_id: Optional[str] = None
    status: str
    raw_pdf_path: str
    markdown_path: Optional[str] = None
    last_error: Optional[str] = None
    discard_reason: Optional[str] = None
    ready_for_part2: bool = False
    ready_for_part3: bool = False
    handoff_payload: dict[str, Any] = Field(default_factory=dict)
    part2_handoff_payload: dict[str, Any] = Field(default_factory=dict)
    trace_events: list[Any] = Field(default_factory=list)
    final_document_id: Optional[int] = None
    final_document: Optional[RfpFinalDocumentOut] = None
    conflicts: list[Any] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    metadata: Optional[RfpMetadataOut] = None
    departments: list[DepartmentSectionOut] = Field(default_factory=list)
    # Derived progress for UI (no extra DB column required).
    pipeline_stage: str = "queued"
    can_retry: bool = False
    can_start_draft: bool = False
    can_start_approval: bool = False


class RfpTicketCreated(BaseModel):
    ticket_id: str
    status: str
    celery_task_id: Optional[str] = None

