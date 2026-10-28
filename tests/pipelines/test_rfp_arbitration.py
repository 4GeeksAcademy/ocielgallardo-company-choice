"""Unit tests for Part 3 BRIEFING arbitration triggers."""

from __future__ import annotations

from data.pipelines.rfp_intake.arbitration import (
    TRIGGER_BAA_DPA,
    TRIGGER_CAPACITY,
    TRIGGER_PHI,
    apply_arbitration,
    detect_conflicts,
)


def _clean_sections() -> dict:
    return {
        "revenue": {
            "department_id": "revenue",
            "draft_content": "Fees in USD for 800 employees over 12 months.",
            "contains_phi": False,
            "evaluation_results": {"contains_phi": False},
        },
        "clinical": {
            "department_id": "clinical",
            "draft_content": (
                "HealthCore clinics can cover the contracted population "
                "with sufficient staffing capacity."
            ),
            "contains_phi": False,
            "evaluation_results": {"contains_phi": False},
        },
        "compliance": {
            "department_id": "compliance",
            "draft_content": (
                "US client requires a Business Associate Agreement (BAA) "
                "and HIPAA safeguards; no patient identifiers in this proposal."
            ),
            "contains_phi": False,
            "evaluation_results": {"contains_phi": False},
        },
    }


def test_phi_detected_forces_claire_and_blocks_synth():
    sections = _clean_sections()
    sections["revenue"]["contains_phi"] = True
    conflicts = detect_conflicts(
        metadata={"client_country": "US", "contains_phi": False},
        sections=sections,
    )
    assert any(c["trigger_id"] == TRIGGER_PHI for c in conflicts)
    phi = next(c for c in conflicts if c["trigger_id"] == TRIGGER_PHI)
    assert phi["arbiter"] == "Claire Whitfield"
    assert phi["blocking_phi"] is True
    assert "compliance" in phi["force_request_changes_departments"]
    assert "revenue" in phi["force_request_changes_departments"]

    result = apply_arbitration(
        metadata={"client_country": "US"},
        sections=sections,
    )
    assert result["blocking_phi"] is True
    assert result["synthesizer_blocked"] is True
    assert result["force_request_changes"]["revenue"] == "request_changes"


def test_baa_dpa_mismatch_us_missing_baa():
    sections = _clean_sections()
    sections["compliance"]["draft_content"] = (
        "Privacy review complete. No BAA wording here."
    )
    conflicts = detect_conflicts(
        metadata={"client_country": "US"},
        sections=sections,
    )
    assert any(c["trigger_id"] == TRIGGER_BAA_DPA for c in conflicts)
    mismatch = next(c for c in conflicts if c["trigger_id"] == TRIGGER_BAA_DPA)
    assert mismatch["arbiter"] == "Claire Whitfield"
    assert "compliance" in mismatch["force_request_changes_departments"]


def test_baa_dpa_mismatch_uk_missing_dpa():
    sections = _clean_sections()
    sections["compliance"]["draft_content"] = (
        "Includes a Business Associate Agreement (BAA) only — wrong for UK."
    )
    sections["revenue"]["draft_content"] = "Fees in GBP."
    conflicts = detect_conflicts(
        metadata={"client_country": "UK"},
        sections=sections,
    )
    assert any(c["trigger_id"] == TRIGGER_BAA_DPA for c in conflicts)


def test_capacity_vs_population_after_no_phi():
    sections = _clean_sections()
    sections["clinical"]["draft_content"] = (
        "Clinical ops cannot cover the stated headcount; insufficient capacity "
        "at current clinic sites."
    )
    conflicts = detect_conflicts(
        metadata={"client_country": "US", "covered_population": "800 employees"},
        sections=sections,
    )
    assert any(c["trigger_id"] == TRIGGER_CAPACITY for c in conflicts)
    cap = next(c for c in conflicts if c["trigger_id"] == TRIGGER_CAPACITY)
    assert cap["arbiter"] == "Tom Callahan"
    assert set(cap["force_request_changes_departments"]) >= {"revenue", "clinical"}


def test_capacity_suppressed_when_phi_present():
    sections = _clean_sections()
    sections["clinical"]["draft_content"] = (
        "Cannot cover population; insufficient capacity."
    )
    sections["compliance"]["contains_phi"] = True
    conflicts = detect_conflicts(
        metadata={"client_country": "US", "covered_population": "800"},
        sections=sections,
    )
    assert any(c["trigger_id"] == TRIGGER_PHI for c in conflicts)
    assert not any(c["trigger_id"] == TRIGGER_CAPACITY for c in conflicts)


def test_clean_sections_no_conflicts():
    conflicts = detect_conflicts(
        metadata={
            "client_country": "US",
            "covered_population": "800 employees",
            "contains_phi": False,
        },
        sections=_clean_sections(),
    )
    assert conflicts == []
