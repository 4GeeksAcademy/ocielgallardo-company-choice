"""Task submission and status endpoints."""

from __future__ import annotations

from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, status

from services.app.core.deps import get_current_user
from services.app.models.user import UserPublic
from services.app.schemas import TaskStatusResponse
from services.app.tasks.celery_app import celery_app


router = APIRouter(prefix="/tasks", tags=["tasks"])


def _public_state(result: AsyncResult) -> str:
    state = result.state.lower()
    if state in {"pending", "retry"}:
        return "pending"
    if state in {"started", "success", "failure"}:
        return state
    return "pending"


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get the current state of a background task",
)
def get_task_status(
    task_id: str,
    _current_user: UserPublic = Depends(get_current_user),
) -> TaskStatusResponse:
    result = AsyncResult(task_id, app=celery_app)
    state = _public_state(result)
    output: dict[str, Any] = {
        "task_id": task_id,
        "status": state,
    }
    if result.successful():
        output["result"] = result.result
    elif result.failed():
        output["error"] = str(result.result)
    return TaskStatusResponse.model_validate(output)
