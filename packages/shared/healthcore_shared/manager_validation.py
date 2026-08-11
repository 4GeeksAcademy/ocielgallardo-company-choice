"""Field-level validation for incident-manager create and status updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from healthcore_shared.manager_constants import (
    MANAGER_BRANCHES,
    MANAGER_CATEGORIES,
    MANAGER_ORIGINS,
    MANAGER_STATUSES,
    is_allowed_status_transition,
)


@dataclass(frozen=True)
class FieldError:
    field: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message}


def validate_incident_create(payload: dict[str, Any]) -> list[FieldError]:
    """Validate a create payload; return a list of field errors (empty if ok)."""
    errors: list[FieldError] = []

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(
            FieldError("title", "Title is required and cannot be blank.")
        )

    description = payload.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(
            FieldError(
                "description",
                "Description is required and cannot be blank.",
            )
        )

    category = payload.get("category")
    if category not in MANAGER_CATEGORIES:
        errors.append(
            FieldError(
                "category",
                "Category must be one of the allowed HealthCore values.",
            )
        )

    origin = payload.get("origin")
    if origin not in MANAGER_ORIGINS:
        errors.append(
            FieldError(
                "origin",
                "Origin must be customer, branch, or internal.",
            )
        )

    branch = payload.get("branch")
    if branch not in MANAGER_BRANCHES:
        errors.append(
            FieldError(
                "branch",
                "Branch must be a valid HealthCore clinic or central.",
            )
        )

    status = payload.get("status", "open")
    if status is not None and status not in MANAGER_STATUSES:
        errors.append(
            FieldError(
                "status",
                "Status must be open, in_progress, resolved, or discarded.",
            )
        )

    return errors


def validate_status_transition(
    current_status: str, new_status: str
) -> FieldError | None:
    """Validate a status change against the lifecycle rules."""
    if new_status not in MANAGER_STATUSES:
        return FieldError(
            "status",
            "Status must be open, in_progress, resolved, or discarded.",
        )
    if not is_allowed_status_transition(current_status, new_status):
        return FieldError(
            "status",
            (
                f"Cannot change status from '{current_status}' to '{new_status}'. "
                "Resolved and discarded are final; from open use in_progress or "
                "discarded; from in_progress use resolved or discarded."
            ),
        )
    return None
