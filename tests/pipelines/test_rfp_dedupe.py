"""Unit tests for open-question deduplication."""

from __future__ import annotations

from data.pipelines.rfp_intake.dedupe import dedupe_questions


def test_dedupe_questions_drops_near_duplicates() -> None:
    qs = [
        "What is the budget range?",
        "what is the budget range",
        "What is the budget range??",
        "Who owns clinical capacity?",
    ]
    out = dedupe_questions(qs)
    assert len(out) == 2
    assert out[0].startswith("What is the budget")
    assert "clinical" in out[1].lower()
