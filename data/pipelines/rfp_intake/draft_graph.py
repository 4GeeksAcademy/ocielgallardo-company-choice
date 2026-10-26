"""Drafting graph: assignment → gen/eval loops → synthesizer.

Consumes intake handoff (metadata + key_aspects). Does not re-parse the PDF.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from data.pipelines.rfp_intake.departments import DEPARTMENTS, KNOWN_DEPARTMENTS
from data.pipelines.rfp_intake.evaluators import evaluate_section_parallel
from data.pipelines.rfp_intake.generators import generate_department_section
from data.pipelines.rfp_intake.generators._rag_context import fetch_grounding_snippets
from data.pipelines.rfp_intake.guidelines import MAX_GENERATOR_EVALUATOR_ITERATIONS
from data.pipelines.rfp_intake.guidelines import currency_for_country

logger = logging.getLogger(__name__)

OnDepartmentDone = Callable[[dict[str, Any]], None]


def assignment_orchestrator(
    handoff_payload: dict[str, Any],
    metadata: dict[str, Any],
    sections_by_dept: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Map intake workstreams to department generator inputs."""
    key_aspects_root = (handoff_payload or {}).get("key_aspects") or {}
    work: dict[str, dict[str, Any]] = {}
    for dept_id in KNOWN_DEPARTMENTS:
        from_handoff = key_aspects_root.get(dept_id) or {}
        from_db = sections_by_dept.get(dept_id) or {}
        aspects = list(
            from_handoff.get("key_aspects")
            or from_db.get("key_aspects")
            or []
        )
        questions = list(
            from_handoff.get("open_questions")
            or from_db.get("open_questions")
            or handoff_payload.get("open_questions")
            or []
        )
        work[dept_id] = {
            "department_id": dept_id,
            "owner": DEPARTMENTS[dept_id]["owner"],
            "metadata": metadata,
            "key_aspects": aspects,
            "open_questions": questions,
        }
    return work


def _rag_query_for_dept(dept_id: str, metadata: dict[str, Any]) -> str:
    currency = currency_for_country(metadata.get("client_country"))
    if dept_id == "revenue":
        return (
            f"HealthCore occupational health pricing payment terms "
            f"{currency} institutional contract"
        )
    if dept_id == "clinical":
        return "HealthCore clinic capacity occupational health wellness staffing model"
    return "HealthCore HIPAA BAA UK GDPR data processing agreement privacy policy"


def run_department_gen_eval_loop(
    assignment: dict[str, Any],
    *,
    max_iterations: int = MAX_GENERATOR_EVALUATOR_ITERATIONS,
) -> dict[str, Any]:
    """Generate → evaluate → retry with feedback until pass or iteration limit."""
    dept_id = assignment["department_id"]
    metadata = assignment["metadata"]
    key_aspects = assignment["key_aspects"]
    open_questions = assignment["open_questions"]
    # Fetch RAG once per department (not per iteration).
    grounding = fetch_grounding_snippets(_rag_query_for_dept(dept_id, metadata))
    feedback = ""
    draft = ""
    evaluation: dict[str, Any] = {}
    history: list[dict[str, Any]] = []
    needs_human_review = False
    iterations = 0

    for i in range(1, max_iterations + 1):
        iterations = i
        generated = generate_department_section(
            dept_id,
            metadata=metadata,
            key_aspects=key_aspects,
            open_questions=open_questions,
            feedback_for_generator=feedback,
            grounding_snippets=grounding,
        )
        draft = generated.get("draft_content") or ""
        evaluation = evaluate_section_parallel(
            department_id=dept_id,
            draft_content=draft,
            metadata=metadata,
            key_aspects=key_aspects,
        )
        history.append(
            {
                "iteration": i,
                "overall_pass": evaluation.get("overall_pass"),
                "feedback_for_generator": evaluation.get("feedback_for_generator"),
                "violations": (evaluation.get("compliance") or {}).get("violations"),
            }
        )
        if evaluation.get("overall_pass"):
            break
        feedback = str(evaluation.get("feedback_for_generator") or "")
        if i >= max_iterations:
            needs_human_review = True
            logger.info(
                "dept=%s exhausted iterations=%s needs_human_review=1",
                dept_id,
                i,
            )

    return {
        "department_id": dept_id,
        "owner": assignment.get("owner") or DEPARTMENTS[dept_id]["owner"],
        "draft_content": draft,
        "evaluation_results": evaluation,
        "iteration_count": iterations,
        "needs_human_review": needs_human_review,
        "eval_history": history,
        "key_aspects": key_aspects,
        "open_questions": open_questions,
        "contains_phi": bool(evaluation.get("contains_phi")),
    }


def synthesize_part2_handoff(
    ticket_id: str,
    metadata: dict[str, Any],
    department_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build Part 3 handoff: drafts + EvaluationResult per department."""
    sections: dict[str, Any] = {}
    any_nhr = False
    all_pass = True
    for dept_id in KNOWN_DEPARTMENTS:
        result = department_results.get(dept_id) or {}
        nhr = bool(result.get("needs_human_review"))
        overall = bool((result.get("evaluation_results") or {}).get("overall_pass"))
        any_nhr = any_nhr or nhr
        all_pass = all_pass and overall and not nhr
        sections[dept_id] = {
            "department_id": dept_id,
            "owner": result.get("owner") or DEPARTMENTS[dept_id]["owner"],
            "draft_content": result.get("draft_content") or "",
            "evaluation_results": result.get("evaluation_results") or {},
            "iteration_count": int(result.get("iteration_count") or 0),
            "needs_human_review": nhr,
            "contains_phi": bool(result.get("contains_phi")),
            "provisional": nhr,
        }

    return {
        "ticket_id": ticket_id,
        "ready_for_part3": True,
        "metadata": {
            "client_name": metadata.get("client_name"),
            "client_country": metadata.get("client_country"),
            "program_type": metadata.get("program_type"),
            "covered_population": metadata.get("covered_population"),
            "currency_hint": currency_for_country(metadata.get("client_country")),
        },
        "sections": sections,
        "any_needs_human_review": any_nhr,
        "all_sections_passed": all_pass,
        "next_step": (
            "Human approval may start from this handoff; "
            "provisional sections are flagged needs_human_review."
        ),
    }


def run_drafting_graph(
    *,
    ticket_id: str,
    metadata: dict[str, Any],
    handoff_payload: dict[str, Any],
    sections_by_dept: dict[str, dict[str, Any]],
    max_iterations: int = MAX_GENERATOR_EVALUATOR_ITERATIONS,
    on_department_done: OnDepartmentDone | None = None,
) -> dict[str, Any]:
    """Run assignment + sequential department gen/eval loops + synthesizer.

    Departments run sequentially so Celery workers never nest ThreadPools
    against hanging LLM/RAG clients. Heuristic drafts keep this fast.
    """
    assignments = assignment_orchestrator(
        handoff_payload, metadata, sections_by_dept
    )
    department_results: dict[str, dict[str, Any]] = {}

    for dept_id in KNOWN_DEPARTMENTS:
        logger.info("drafting dept=%s ticket_id=%s", dept_id, ticket_id)
        result = run_department_gen_eval_loop(
            assignments[dept_id],
            max_iterations=max_iterations,
        )
        department_results[dept_id] = result
        if on_department_done:
            try:
                on_department_done(result)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "on_department_done failed dept=%s ticket_id=%s",
                    dept_id,
                    ticket_id,
                )

    part2_handoff = synthesize_part2_handoff(
        ticket_id, metadata, department_results
    )
    terminal = (
        "needs_human_review"
        if part2_handoff.get("any_needs_human_review")
        else "under_evaluation"
    )
    return {
        "ticket_id": ticket_id,
        "status": terminal,
        "ready_for_part3": True,
        "department_results": department_results,
        "part2_handoff_payload": part2_handoff,
    }
