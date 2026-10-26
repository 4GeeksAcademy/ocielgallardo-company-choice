"""Unit tests for the revenue department worker agent."""

from __future__ import annotations

from data.pipelines.rfp_intake.workers import analyze_department_heuristic


def test_revenue_worker_uses_stated_population_and_usd_for_us() -> None:
    result = analyze_department_heuristic(
        "revenue",
        "Budget discussion in USD for a 12-month occupational health contract.",
        {
            "client_name": "Meridian Manufacturing",
            "client_country": "US",
            "program_type": "occupational_health",
            "covered_population": "800",
            "budget_range": None,
            "deadline": None,
        },
    )
    assert result["department_id"] == "revenue"
    assert result["owner"] == "Tom Callahan"
    joined = " ".join(result["key_aspects"]).lower()
    assert "800" in joined
    assert "usd" in joined
    assert not any("invent" in q.lower() and "800" in q for q in result["open_questions"])


def test_revenue_worker_does_not_invent_missing_headcount() -> None:
    result = analyze_department_heuristic(
        "revenue",
        "Please send pricing for a wellness partnership. Marketing wants a brochure.",
        {
            "client_name": "Example Corp",
            "client_country": "UK",
            "program_type": "corporate_wellness",
            "covered_population": None,
            "budget_range": None,
            "deadline": None,
        },
        orchestrator_questions=[],
    )
    joined = " ".join(result["key_aspects"]).lower()
    assert "not stated" in joined or "do not invent" in joined
    # Must not fabricate a numeric headcount
    assert "1000" not in joined
    assert "500" not in joined
    assert any("population" in q.lower() or "headcount" in q.lower() for q in result["open_questions"])
    assert result["owner"] == "Tom Callahan"


def test_compliance_worker_requires_dpa_for_uk() -> None:
    result = analyze_department_heuristic(
        "compliance",
        "Partnership in the United Kingdom requiring privacy terms.",
        {
            "client_name": "Thames Valley University",
            "client_country": "UK",
            "program_type": "referral_network",
            "covered_population": None,
        },
    )
    joined = " ".join(result["key_aspects"]).lower()
    assert "dpa" in joined or "gdpr" in joined
    assert result["owner"] == "Claire Whitfield"
