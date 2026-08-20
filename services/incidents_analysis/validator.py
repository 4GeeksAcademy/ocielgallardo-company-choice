"""CSV incident validation — re-exports shared HealthCore rules."""

from healthcore_shared.csv_validation import (
    VALID_CATEGORIES,
    VALID_CLINICS,
    first_failure_reason,
    validate_incidents,
)

# Backwards-compatible private alias used by older call sites / tests.
_first_failure_reason = first_failure_reason

__all__ = [
    "VALID_CATEGORIES",
    "VALID_CLINICS",
    "_first_failure_reason",
    "first_failure_reason",
    "validate_incidents",
]
