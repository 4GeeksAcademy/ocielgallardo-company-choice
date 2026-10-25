"""Unit tests for PHI detect/redact in RFP intake."""

from __future__ import annotations

from data.pipelines.rfp_intake.phi import detect_and_redact_phi


def test_phi_redacts_patient_name_and_diagnosis() -> None:
    text = (
        "Attached clinical case summary for Patient Jane Doe. "
        "Diagnosis: Type 2 diabetes. MRN 998877."
    )
    result = detect_and_redact_phi(text)
    assert result["contains_phi"] is True
    assert "Jane Doe" not in result["text"]
    assert "[REDACTED_PHI]" in result["text"]


def test_clean_rfp_has_no_phi() -> None:
    text = (
        "Meridian Manufacturing requests occupational health for 800 employees "
        "in Austin, United States, including a BAA under HIPAA."
    )
    result = detect_and_redact_phi(text)
    assert result["contains_phi"] is False
    assert result["text"] == text
