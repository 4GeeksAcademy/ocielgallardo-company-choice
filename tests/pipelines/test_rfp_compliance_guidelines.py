"""BRIEFING §5 anchored compliance failures for Part 2 evaluator."""

from __future__ import annotations

from data.pipelines.rfp_intake.evaluators.compliance import evaluate_compliance


def test_us_draft_with_patient_phi_fails_no_phi_rule() -> None:
    """BRIEFING: no section may contain patient names/diagnoses (even illustrative)."""
    draft = (
        "Compliance section for Meridian Manufacturing (US).\n"
        "We include a Business Associate Agreement (BAA) under HIPAA.\n"
        "Currency note: USD.\n"
        "Attached clinical case summary for Patient Jane Doe. Diagnosis: Type 2 diabetes.\n"
    )
    result = evaluate_compliance(
        draft,
        metadata={"client_country": "US", "client_name": "Meridian Manufacturing"},
        department_id="compliance",
    )
    assert result["pass"] is False
    assert "no-phi" in result["violations"]
    assert result["contains_phi"] is True


def test_us_compliance_draft_missing_baa_fails_baa_rule() -> None:
    """BRIEFING: every US proposal must include a BAA clause."""
    draft = (
        "## Compliance\n"
        "Claire Whitfield will review regulatory posture for this US client.\n"
        "We will protect privacy and avoid PHI in the proposal.\n"
        "No patient identifiers appear here. Currency for commercial terms is USD.\n"
        "This text is long enough for a basic compliance narrative without naming the "
        "required contractual instrument for United States clients.\n"
    )
    result = evaluate_compliance(
        draft,
        metadata={"client_country": "US"},
        department_id="compliance",
    )
    assert result["pass"] is False
    assert "baa-required-us" in result["violations"]


def test_clean_us_compliance_draft_passes() -> None:
    draft = (
        "## Compliance and Data Governance\n"
        "Mandatory Compliance review for Meridian Manufacturing (US).\n"
        "A Business Associate Agreement (BAA) under HIPAA will be executed.\n"
        "This proposal contains no patient names, diagnoses, or patient identifiers.\n"
        "Commercial currency alignment: USD.\n"
        "Owner: Claire Whitfield.\n"
    )
    result = evaluate_compliance(
        draft,
        metadata={"client_country": "US"},
        department_id="compliance",
    )
    assert result["pass"] is True
    assert result["violations"] == []
