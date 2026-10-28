"""Unit tests for Part 3 final document synthesizer."""

from __future__ import annotations

import pytest

from data.pipelines.rfp_intake.final_document import (
    FinalDocumentError,
    synthesize_final_document,
)


def _approved_sections() -> dict:
    return {
        "revenue": {
            "draft_content": "## Revenue\nUSD fees for Meridian.",
            "contains_phi": False,
            "evaluation_results": {"contains_phi": False},
            "approval_status": "approved",
            "approver": "Tom Callahan",
        },
        "clinical": {
            "draft_content": "## Clinical\nCapacity confirmed for 800 employees.",
            "contains_phi": False,
            "evaluation_results": {"contains_phi": False},
            "approval_status": "approved",
            "approver": "Dr. Marcus Reid",
        },
        "compliance": {
            "draft_content": "## Compliance\nBAA and HIPAA controls included.",
            "contains_phi": False,
            "evaluation_results": {"contains_phi": False},
            "approval_status": "approved",
            "approver": "Claire Whitfield",
        },
    }


def test_synthesize_succeeds_with_three_approved_clean_drafts():
    doc = synthesize_final_document(
        ticket_id="t-1",
        metadata={
            "client_name": "Meridian Manufacturing",
            "client_country": "US",
            "program_type": "occupational health",
            "covered_population": "800 employees",
        },
        sections=_approved_sections(),
    )
    assert doc["currency"] == "USD"
    assert "Meridian Manufacturing" in doc["content_markdown"]
    assert "Revenue Cycle" in doc["content_markdown"]
    assert "Clinical Operations" in doc["content_markdown"]
    assert "Compliance and Data Governance" in doc["content_markdown"]
    assert set(doc["sections"].keys()) == {"revenue", "clinical", "compliance"}


def test_synthesize_refuses_phi():
    sections = _approved_sections()
    sections["clinical"]["contains_phi"] = True
    with pytest.raises(FinalDocumentError, match="contains_phi"):
        synthesize_final_document(
            ticket_id="t-1",
            metadata={"client_country": "US"},
            sections=sections,
        )


def test_synthesize_refuses_missing_compliance_approval():
    sections = _approved_sections()
    sections["compliance"]["approval_status"] = "pending"
    with pytest.raises(FinalDocumentError, match="compliance"):
        synthesize_final_document(
            ticket_id="t-1",
            metadata={"client_country": "US"},
            sections=sections,
            approvals={
                "revenue": {"approval_status": "approved"},
                "clinical": {"approval_status": "approved"},
                "compliance": {"approval_status": "pending"},
            },
        )


def test_uk_currency_gbp():
    sections = _approved_sections()
    doc = synthesize_final_document(
        ticket_id="t-uk",
        metadata={"client_name": "Thames Valley", "client_country": "UK"},
        sections=sections,
    )
    assert doc["currency"] == "GBP"
