"""Readability evaluator using py-readability-metrics."""

from __future__ import annotations

from typing import Any

from data.pipelines.rfp_intake.readability import compute_readability_metrics

# B2B proposal: prefer not extremely hard (FK grade <= 16) and enough length.
_MIN_WORDS = 40
_MAX_FK_GRADE = 16.0


def evaluate_readability(draft_content: str) -> dict[str, Any]:
    text = (draft_content or "").strip()
    metrics = compute_readability_metrics(text)
    word_count = int(metrics.get("word_count") or 0)
    fk = metrics.get("flesch_kincaid_grade")
    ease = metrics.get("flesch_reading_ease")

    failures: list[str] = []
    if word_count < _MIN_WORDS:
        failures.append(f"Draft too short ({word_count} words; need >= {_MIN_WORDS}).")
    if fk is not None and float(fk) > _MAX_FK_GRADE:
        failures.append(
            f"Flesch-Kincaid grade {fk:.1f} exceeds {_MAX_FK_GRADE} (simplify sentences)."
        )
    if not text:
        failures.append("Empty draft.")

    passed = len(failures) == 0
    score = float(ease) if ease is not None else (float(fk) if fk is not None else None)
    details = (
        f"words={word_count}; fk_grade={fk}; reading_ease={ease}. "
        + ("OK for B2B proposal." if passed else " ".join(failures))
    )
    return {
        "pass": passed,
        "score": score,
        "details": details.strip(),
        "metrics": metrics,
        "failures": failures,
    }
