"""Merge parallel evaluator partials into a structured EvaluationResult."""

from __future__ import annotations

from typing import Any


def merge_evaluation_results(
    *,
    department_id: str,
    readability: dict[str, Any],
    relevance: dict[str, Any],
    compliance: dict[str, Any],
) -> dict[str, Any]:
    read_pass = bool(readability.get("pass"))
    rel_pass = bool(relevance.get("pass"))
    comp_pass = bool(compliance.get("pass"))
    overall = read_pass and rel_pass and comp_pass

    feedback_parts: list[str] = []
    if not read_pass:
        details = readability.get("details") or "Improve readability."
        failures = readability.get("failures") or []
        if failures:
            feedback_parts.append(
                "Readability: " + "; ".join(str(f) for f in failures)
            )
        else:
            feedback_parts.append(f"Readability: {details}")
    if not rel_pass:
        missing = relevance.get("missing_aspects") or []
        if missing:
            feedback_parts.append(
                "Relevance — cover missing aspects: " + "; ".join(missing)
            )
        else:
            feedback_parts.append("Relevance: draft does not address Part 1 aspects.")
    if not comp_pass:
        violations = compliance.get("violations") or []
        if violations:
            feedback_parts.append(
                "Compliance — fix rule_ids: "
                + ", ".join(violations)
                + ". Cite BRIEFING §5; do not invent PHI or wrong currency/instrument."
            )
        else:
            feedback_parts.append("Compliance: failed BRIEFING §5 checks.")

    if overall:
        feedback = "All evaluators passed."
    else:
        feedback = " ".join(feedback_parts) if feedback_parts else "Evaluation failed."

    return {
        "section_id": department_id,
        "department_id": department_id,
        "readability": {
            "pass": read_pass,
            "score": readability.get("score"),
            "details": readability.get("details") or "",
        },
        "relevance": {
            "pass": rel_pass,
            "missing_aspects": list(relevance.get("missing_aspects") or []),
        },
        "compliance": {
            "pass": comp_pass,
            "rule_ids": list(compliance.get("rule_ids") or []),
            "violations": list(compliance.get("violations") or []),
        },
        "overall_pass": overall,
        "feedback_for_generator": feedback,
        "contains_phi": bool(compliance.get("contains_phi")),
    }
