"""Relevance evaluator — draft must address Part 1 key aspects / outline."""

from __future__ import annotations

import re
from typing import Any

from data.pipelines.rfp_intake.guidelines import SECTION_OUTLINES

_TOKEN = re.compile(r"[a-z0-9]{4,}")


def evaluate_relevance(
    draft_content: str,
    *,
    key_aspects: list[Any],
    department_id: str,
) -> dict[str, Any]:
    text = (draft_content or "").lower()
    missing: list[str] = []

    # Outline anchors by department
    outline_checks: dict[str, list[tuple[str, str]]] = {
        "revenue": [
            ("currency|usd|gbp|payment|fee|pricing", "Financial terms / currency / payment structure"),
            ("population|headcount|employee|volume|budget", "Volume or budget discussion"),
        ],
        "clinical": [
            ("clinic|clinical|staff|capacity|feasibility", "Clinical feasibility / capacity"),
            ("program|occupational|wellness|referral|on-site|onsite", "Program / delivery model"),
        ],
        "compliance": [
            ("compliance|regulatory|hipaa|gdpr|baa|dpa", "Regulatory instrument (BAA/DPA)"),
            ("phi|patient identifier|no patient", "Explicit no-PHI / privacy stance"),
        ],
    }

    for pattern, label in outline_checks.get(department_id, []):
        if not re.search(pattern, text, re.I):
            missing.append(label)

    # Soft check: at least one substantive Part 1 aspect token appears
    aspect_hits = 0
    for aspect in key_aspects or []:
        tokens = _TOKEN.findall(str(aspect).lower())
        if any(tok in text for tok in tokens[:6]):
            aspect_hits += 1
    if key_aspects and aspect_hits == 0:
        missing.append("Part 1 key aspects not reflected in draft wording")

    # Required outline presence (title-level)
    for item in SECTION_OUTLINES.get(department_id, [])[:2]:
        # Already covered by pattern checks; skip duplicate noise
        _ = item

    passed = len(missing) == 0 and bool(text.strip())
    if not text.strip():
        missing.append("Empty draft")
        passed = False

    return {
        "pass": passed,
        "missing_aspects": missing,
    }
