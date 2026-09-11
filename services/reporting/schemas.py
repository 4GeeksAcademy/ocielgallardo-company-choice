"""Pydantic models for /reporting endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class PipelineRunResponse(BaseModel):
    """Latest (or just-triggered) pipeline_runs metadata."""

    run_id: str
    pipeline_name: str | None = None
    month_start: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    status: str | None = None
    phase: str | None = None
    records_processed: int | None = None
    records_extracted: int | None = None
    window_start: str | None = None
    window_end: str | None = None
    error_message: str | None = None
    eval_snapshot_ok: bool | None = None

    model_config = {"extra": "allow"}


class TriggerPipelineRunRequest(BaseModel):
    """Optional body for POST /reporting/pipeline-runs."""

    month_start: date | None = Field(
        default=None,
        description="First day of the month to compute (UTC). Defaults to previous calendar month.",
    )


class ClinicSupplyPerformanceRow(BaseModel):
    clinic_id: str
    country: str
    total_supply_cost: float
    supply_consumption_count: int
    critical_stockout_count: int
    expiry_risk_count: int
    currency: str


class MonthlyClinicSupplyPerformanceResponse(BaseModel):
    month_start: str | None
    clinics: list[ClinicSupplyPerformanceRow]


def pipeline_run_from_dict(data: dict[str, Any]) -> PipelineRunResponse:
    return PipelineRunResponse.model_validate(data)
