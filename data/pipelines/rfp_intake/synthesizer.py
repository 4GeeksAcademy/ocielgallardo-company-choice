"""Synthesizer: consolidate department analyses into a Sales handoff for Part 2."""

from __future__ import annotations

from typing import Any

from data.pipelines.rfp_intake.dedupe import dedupe_questions
from data.pipelines.rfp_intake.departments import DEPARTMENTS, KNOWN_DEPARTMENTS


def synthesize_handoff(
    ticket_id: str,
    metadata: dict[str, Any],
    worker_results: dict[str, dict[str, Any]],
    *,
    orchestrator_open_questions: list[str] | None = None,
) -> dict[str, Any]:
    """Build Part 2 handoff payload + human-readable ask-who summary."""
    conflicts: list[str] = []
    # Example soft conflict: population mentioned differently — workers only store aspects.
    populations = []
    for dept_id, result in worker_results.items():
        for aspect in result.get("key_aspects") or []:
            if "population" in aspect.lower() and "not stated" not in aspect.lower():
                populations.append((dept_id, aspect))
    if len({p[1] for p in populations}) > 1:
        conflicts.append(
            "Workers reported differing population statements; Revenue Cycle must reconcile before drafting."
        )

    ask_who: list[dict[str, Any]] = []
    key_aspects_by_dept: dict[str, Any] = {}
    all_questions: list[str] = list(orchestrator_open_questions or [])

    for dept_id in KNOWN_DEPARTMENTS:
        result = worker_results.get(dept_id) or {
            "key_aspects": [],
            "open_questions": [],
            "owner": DEPARTMENTS[dept_id]["owner"],
            "contains_phi": False,
        }
        owner = result.get("owner") or DEPARTMENTS[dept_id]["owner"]
        aspects = list(result.get("key_aspects") or [])
        questions = dedupe_questions(list(result.get("open_questions") or []))
        key_aspects_by_dept[dept_id] = {
            "owner": owner,
            "department_name": DEPARTMENTS[dept_id]["name"],
            "key_aspects": aspects,
            "open_questions": questions,
            "contains_phi": bool(result.get("contains_phi")),
        }
        ask_who.append(
            {
                "department_id": dept_id,
                "ask": DEPARTMENTS[dept_id]["name"],
                "contact": owner,
                "needs": aspects[:5],
                "open_questions": questions,
            }
        )
        all_questions.extend(questions)

    all_questions = dedupe_questions(all_questions)

    contains_phi = any(
        bool((worker_results.get(d) or {}).get("contains_phi")) for d in KNOWN_DEPARTMENTS
    ) or bool(metadata.get("contains_phi"))

    sales_summary = {
        "headline": (
            f"Intake complete for {metadata.get('client_name') or 'client TBD'} "
            f"({metadata.get('client_country') or 'country TBD'})"
        ),
        "what_to_ask_whom": ask_who,
        "conflicts": conflicts,
        "contains_phi": contains_phi,
        "next_step": (
            "Part 2 may start using ticket_id + this handoff_payload; "
            "do not re-parse the PDF."
        ),
    }

    return {
        "ticket_id": ticket_id,
        "ready_for_part2": True,
        "metadata": {
            "client_name": metadata.get("client_name"),
            "client_country": metadata.get("client_country"),
            "program_type": metadata.get("program_type"),
            "covered_population": metadata.get("covered_population"),
            "deadline": metadata.get("deadline"),
            "budget_range": metadata.get("budget_range"),
            "departments_needed": list(KNOWN_DEPARTMENTS),
        },
        "key_aspects": key_aspects_by_dept,
        "open_questions": all_questions,
        "conflicts": conflicts,
        "sales_summary": sales_summary,
        "contains_phi": contains_phi,
    }
