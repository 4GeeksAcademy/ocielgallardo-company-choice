"""Unit tests for the Revenue Cycle Part 2 generator."""

from __future__ import annotations

from data.pipelines.rfp_intake.generators.revenue import generate_revenue_section


def test_revenue_generator_uses_usd_for_us_and_stated_population() -> None:
    result = generate_revenue_section(
        metadata={
            "client_name": "Meridian Manufacturing",
            "client_country": "US",
            "program_type": "occupational_health",
            "covered_population": "800",
            "deadline": "30 days",
            "budget_range": None,
            "contains_phi": False,
        },
        key_aspects=[
            "Client: Meridian Manufacturing (US)",
            "Quote currency: USD",
            "Covered population stated: 800",
        ],
        open_questions=[],
    )
    draft = result["draft_content"].lower()
    assert result["department_id"] == "revenue"
    assert "usd" in draft
    assert "800" in draft
    assert "tom callahan" in draft
    assert "patient jane" not in draft


def test_revenue_generator_uses_gbp_for_uk() -> None:
    result = generate_revenue_section(
        metadata={
            "client_name": "Thames Valley University",
            "client_country": "UK",
            "program_type": "referral_network",
            "covered_population": None,
            "contains_phi": False,
        },
        key_aspects=["Quote currency: GBP"],
        open_questions=["Confirm covered student volume"],
    )
    draft = result["draft_content"].lower()
    assert "gbp" in draft
    assert "not stated" in draft or "clarification" in draft
