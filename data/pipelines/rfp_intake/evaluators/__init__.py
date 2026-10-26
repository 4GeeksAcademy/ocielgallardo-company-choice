"""Part 2 parallel evaluators + merge into EvaluationResult."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from data.pipelines.rfp_intake.evaluators.compliance import evaluate_compliance
from data.pipelines.rfp_intake.evaluators.merge import merge_evaluation_results
from data.pipelines.rfp_intake.evaluators.readability import evaluate_readability
from data.pipelines.rfp_intake.evaluators.relevance import evaluate_relevance


def evaluate_section_parallel(
    *,
    department_id: str,
    draft_content: str,
    metadata: dict[str, Any],
    key_aspects: list[Any],
) -> dict[str, Any]:
    """Run readability, relevance, and compliance evaluators in parallel; merge."""
    partials: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(evaluate_readability, draft_content): "readability",
            pool.submit(
                evaluate_relevance,
                draft_content,
                key_aspects=key_aspects,
                department_id=department_id,
            ): "relevance",
            pool.submit(
                evaluate_compliance,
                draft_content,
                metadata=metadata,
                department_id=department_id,
            ): "compliance",
        }
        for fut in as_completed(futures):
            name = futures[fut]
            partials[name] = fut.result()

    return merge_evaluation_results(
        department_id=department_id,
        readability=partials.get("readability") or {},
        relevance=partials.get("relevance") or {},
        compliance=partials.get("compliance") or {},
    )


__all__ = ["evaluate_section_parallel"]
