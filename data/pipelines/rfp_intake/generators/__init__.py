"""Per-department proposal section generators (Part 2)."""

from __future__ import annotations

from typing import Any, Callable

from data.pipelines.rfp_intake.generators.clinical import generate_clinical_section
from data.pipelines.rfp_intake.generators.compliance import generate_compliance_section
from data.pipelines.rfp_intake.generators.revenue import generate_revenue_section

_GENERATORS: dict[str, Callable[..., dict[str, Any]]] = {
    "revenue": generate_revenue_section,
    "clinical": generate_clinical_section,
    "compliance": generate_compliance_section,
}


def generate_department_section(
    department_id: str,
    *,
    metadata: dict[str, Any],
    key_aspects: list[Any],
    open_questions: list[Any] | None = None,
    feedback_for_generator: str | None = None,
    grounding_snippets: list[str] | None = None,
) -> dict[str, Any]:
    fn = _GENERATORS.get(department_id)
    if not fn:
        raise ValueError(f"No generator for department_id={department_id}")
    return fn(
        metadata=metadata,
        key_aspects=key_aspects,
        open_questions=open_questions or [],
        feedback_for_generator=feedback_for_generator or "",
        grounding_snippets=grounding_snippets,
    )


__all__ = ["generate_department_section"]
