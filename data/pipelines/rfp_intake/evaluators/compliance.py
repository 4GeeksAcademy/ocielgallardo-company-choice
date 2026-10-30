"""Compliance evaluator — BRIEFING §5 rule_ids (not free-form style)."""

from __future__ import annotations

import re
from typing import Any

from data.pipelines.rfp_intake.guidelines import rules_for_country
from data.pipelines.rfp_intake.phi import detect_and_redact_phi


def evaluate_compliance(
    draft_content: str,
    *,
    metadata: dict[str, Any],
    department_id: str,
) -> dict[str, Any]:
    text = draft_content or ""
    country = metadata.get("client_country")
    applicable = rules_for_country(country if isinstance(country, str) else None)
    violations: list[str] = []

    phi = detect_and_redact_phi(text)
    contains_phi = bool(phi.get("contains_phi"))
    if contains_phi or _looks_like_illustrative_patient(text):
        violations.append("no-phi")

    # Currency / instrument rules apply to every section for country consistency,
    # with stricter checks on revenue (currency) and compliance (BAA/DPA).
    lower = text.lower()
    if country == "US":
        if department_id in {"revenue", "compliance"}:
            if "usd" not in lower and "u.s. dollar" not in lower:
                if department_id == "revenue":
                    violations.append("currency-usd-us")
        if department_id == "compliance":
            if "baa" not in lower and "business associate" not in lower:
                violations.append("baa-required-us")
    elif country == "UK":
        if department_id in {"revenue", "compliance"}:
            if "gbp" not in lower and "pound" not in lower:
                if department_id == "revenue":
                    violations.append("currency-gbp-uk")
        if department_id == "compliance":
            if "dpa" not in lower and "data processing" not in lower:
                violations.append("dpa-required-uk")
            if "gdpr" not in lower and "uk gdpr" not in lower:
                if "dpa-required-uk" not in violations:
                    violations.append("dpa-required-uk")

    # Dedupe while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for v in violations:
        if v not in seen:
            seen.add(v)
            uniq.append(v)

    passed = len(uniq) == 0
    return {
        "pass": passed,
        "rule_ids": list(applicable),
        "violations": uniq,
        "contains_phi": contains_phi or ("no-phi" in uniq),
    }


def _looks_like_illustrative_patient(text: str) -> bool:
    """Catch illustrative PHI the heuristic may miss (BRIEFING forbids even examples).

    Avoid false positives on policy phrases like "no patient names or identifiers".
    """
    return bool(
        re.search(
            r"\b(?:patient\s+(?:name|id)\s*[:\-]\s*\w+|diagnosis\s*:\s*\w+|mrn\s*\d+|ssn\s*[:\-]?\s*\d)",
            text,
            re.I,
        )
    )
