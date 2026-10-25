"""HealthCore BRIEFING §5 compliance rules + Part 2 section outlines.

Evaluators check these rule_ids — not free-form style opinions.
"""

from __future__ import annotations

from typing import Any, TypedDict


class ComplianceRule(TypedDict):
    rule_id: str
    description: str


# BRIEFING §5 — Business Constraints (Guidelines for the Compliance Evaluator)
COMPLIANCE_RULES: tuple[ComplianceRule, ...] = (
    {
        "rule_id": "no-phi",
        "description": (
            "No generated section may contain patient names, diagnoses, "
            "or any patient identifier, real or illustrative."
        ),
    },
    {
        "rule_id": "baa-required-us",
        "description": "Every proposal for a US client must include a Business Associate Agreement (BAA) clause.",
    },
    {
        "rule_id": "dpa-required-uk",
        "description": (
            "Every proposal for a UK client must include a Data Processing Agreement (DPA) "
            "clause referencing UK GDPR."
        ),
    },
    {
        "rule_id": "currency-usd-us",
        "description": "Pricing is quoted in USD for US clients (client_country=US).",
    },
    {
        "rule_id": "currency-gbp-uk",
        "description": "Pricing is quoted in GBP for UK clients (client_country=UK).",
    },
)

RULE_IDS = {r["rule_id"] for r in COMPLIANCE_RULES}

MAX_GENERATOR_EVALUATOR_ITERATIONS = 3

# Per-department proposal section outlines (what generators must cover).
SECTION_OUTLINES: dict[str, list[str]] = {
    "revenue": [
        "Financial terms and payment structure",
        "Quote currency aligned to client country (USD or GBP)",
        "Covered population / volume (only if stated in Part 1 metadata — never invent)",
        "Contract term / deadline signals from the RFP",
        "Owner: Tom Callahan (Revenue Cycle)",
    ],
    "clinical": [
        "Clinical feasibility for the requested program type",
        "Clinic / staff capacity relative to stated population (or open question if unknown)",
        "Delivery model (on-site, referral network, satellite) when present in Part 1 aspects",
        "Owner: Dr. Marcus Reid (Clinical Operations)",
    ],
    "compliance": [
        "Mandatory Compliance review statement",
        "US → BAA clause; UK → DPA / UK GDPR clause",
        "Explicit confirmation that no PHI / patient identifiers appear in the proposal",
        "Owner: Claire Whitfield (Compliance and Data Governance)",
    ],
}


def currency_for_country(client_country: str | None) -> str:
    if client_country == "US":
        return "USD"
    if client_country == "UK":
        return "GBP"
    return "TBD"


def rules_for_country(client_country: str | None) -> list[str]:
    """Rule ids that apply given client_country (always includes no-phi)."""
    ids = ["no-phi"]
    if client_country == "US":
        ids.extend(["baa-required-us", "currency-usd-us"])
    elif client_country == "UK":
        ids.extend(["dpa-required-uk", "currency-gbp-uk"])
    return ids


def evaluation_result_template(
    department_id: str,
    *,
    overall_pass: bool = False,
) -> dict[str, Any]:
    return {
        "section_id": department_id,
        "department_id": department_id,
        "readability": {"pass": False, "score": None, "details": ""},
        "relevance": {"pass": False, "missing_aspects": []},
        "compliance": {"pass": False, "rule_ids": [], "violations": []},
        "overall_pass": overall_pass,
        "feedback_for_generator": "",
        "contains_phi": False,
    }
