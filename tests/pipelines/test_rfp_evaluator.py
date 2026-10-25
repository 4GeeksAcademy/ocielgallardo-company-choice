"""Unit tests for Part 2 evaluators (generic fail + merge)."""

from __future__ import annotations

from data.pipelines.rfp_intake.evaluators import evaluate_section_parallel
from data.pipelines.rfp_intake.evaluators.merge import merge_evaluation_results
from data.pipelines.rfp_intake.evaluators.readability import evaluate_readability
from data.pipelines.rfp_intake.evaluators.relevance import evaluate_relevance


def test_empty_draft_fails_readability_and_relevance() -> None:
    read = evaluate_readability("")
    rel = evaluate_relevance(
        "",
        key_aspects=["Quote currency: USD", "Covered population stated: 800"],
        department_id="revenue",
    )
    assert read["pass"] is False
    assert rel["pass"] is False
    assert "Empty draft" in rel["missing_aspects"] or rel["missing_aspects"]


def test_irrelevant_short_draft_overall_fail() -> None:
    draft = "Hello world."
    result = evaluate_section_parallel(
        department_id="revenue",
        draft_content=draft,
        metadata={"client_country": "US", "client_name": "Meridian"},
        key_aspects=["Quote currency: USD", "Covered population stated: 800"],
    )
    assert result["overall_pass"] is False
    assert "feedback_for_generator" in result
    assert result["feedback_for_generator"]


def test_merge_builds_structured_evaluation_result() -> None:
    merged = merge_evaluation_results(
        department_id="clinical",
        readability={"pass": True, "score": 60.0, "details": "ok"},
        relevance={"pass": False, "missing_aspects": ["Clinical feasibility / capacity"]},
        compliance={"pass": True, "rule_ids": ["no-phi"], "violations": [], "contains_phi": False},
    )
    assert merged["section_id"] == "clinical"
    assert merged["overall_pass"] is False
    assert merged["relevance"]["missing_aspects"] == ["Clinical feasibility / capacity"]
    assert "Relevance" in merged["feedback_for_generator"]
