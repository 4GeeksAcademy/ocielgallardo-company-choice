"""Authenticated reporting endpoints for Monthly Clinic Supply Performance.

No ETL logic here — all work is delegated to ``data.pipelines.pipeline``.
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.app.core.deps import get_current_user
from services.app.core.database import is_inventory_db_configured
from services.app.models.user import UserPublic
from services.reporting.schemas import (
    MonthlyClinicSupplyPerformanceResponse,
    PipelineRunResponse,
    TriggerPipelineRunRequest,
    pipeline_run_from_dict,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reporting", tags=["reporting"])


def _require_db() -> None:
    if not is_inventory_db_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reporting requires DATABASE_URL or SUPABASE_DB_* in .env",
        )


@router.get(
    "/pipeline-runs/latest",
    response_model=PipelineRunResponse,
    summary="Latest pipeline run metadata",
)
def get_latest_pipeline_run_endpoint(
    _current_user: UserPublic = Depends(get_current_user),
) -> PipelineRunResponse:
    """Return status/metadata of the most recent monthly clinic supply run."""
    _require_db()
    from data.pipelines.pipeline import get_latest_pipeline_run

    row = get_latest_pipeline_run()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pipeline runs found",
        )
    return pipeline_run_from_dict(row)


@router.post(
    "/pipeline-runs",
    response_model=PipelineRunResponse,
    summary="Trigger a monthly clinic supply performance run",
)
def trigger_pipeline_run_endpoint(
    body: TriggerPipelineRunRequest | None = None,
    month_start: date | None = Query(
        default=None,
        description="Optional month_start (ISO date). Overrides body when both set.",
    ),
    _current_user: UserPublic = Depends(get_current_user),
) -> PipelineRunResponse:
    """Run the ETL synchronously (same path as CLI when Prefect API is unset)."""
    _require_db()
    from data.pipelines.pipeline import trigger_monthly_clinic_supply_performance_run

    resolved = month_start
    if resolved is None and body is not None:
        resolved = body.month_start

    try:
        result = trigger_monthly_clinic_supply_performance_run(month_start=resolved)
    except RuntimeError as exc:
        logger.exception("pipeline trigger failed (config)")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001 — surface ETL failure to client
        logger.exception("pipeline trigger failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline run failed: {exc}",
        ) from exc

    return pipeline_run_from_dict(result)


@router.get(
    "/monthly-clinic-supply-performance",
    response_model=MonthlyClinicSupplyPerformanceResponse,
    summary="Monthly clinic supply performance KPIs",
)
def get_monthly_clinic_supply_performance(
    month_start: date | None = Query(
        default=None,
        description="First day of month (UTC). Defaults to the latest computed month.",
    ),
    _current_user: UserPublic = Depends(get_current_user),
) -> MonthlyClinicSupplyPerformanceResponse:
    """Return CONTEXT KPI rows for one month (clinic_id as text \"1\"–\"12\")."""
    _require_db()
    from data.pipelines.pipeline import query_monthly_clinic_supply_performance

    try:
        payload = query_monthly_clinic_supply_performance(month_start=month_start)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return MonthlyClinicSupplyPerformanceResponse.model_validate(payload)
