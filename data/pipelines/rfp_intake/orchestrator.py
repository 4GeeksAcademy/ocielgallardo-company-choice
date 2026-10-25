"""Orchestrator: decompose Markdown into department workstreams."""

from __future__ import annotations

import re
from typing import Any

from data.pipelines.rfp_intake.departments import (
    DEPARTMENT_KEYWORDS,
    KNOWN_DEPARTMENTS,
)


_UNKNOWN_DEPT_HINTS = re.compile(
    r"\b(?:marketing|legal|it department|engineering|hr department|"
    r"human resources|procurement)\b",
    re.IGNORECASE,
)


def _paragraphs(markdown: str) -> list[str]:
    parts = re.split(r"\n\s*\n", markdown or "")
    return [p.strip() for p in parts if p.strip()]


def extract_for_department(markdown: str, department_id: str) -> str:
    """Return paragraphs relevant to a department (not the full document)."""
    keywords = DEPARTMENT_KEYWORDS.get(department_id, ())
    selected: list[str] = []
    for para in _paragraphs(markdown):
        lower = para.lower()
        if any(k in lower for k in keywords):
            selected.append(para)
    if not selected:
        # Minimal shared context: first ~2 paragraphs (still bounded).
        selected = _paragraphs(markdown)[:2]
    text = "\n\n".join(selected)
    # Cap tokens roughly
    return text[:6000]


def find_unknown_departments(markdown: str) -> list[str]:
    found = sorted({m.group(0).lower() for m in _UNKNOWN_DEPT_HINTS.finditer(markdown or "")})
    return found


def plan_workstreams(markdown: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """Always schedule revenue, clinical, compliance (BRIEFING)."""
    workstreams: dict[str, str] = {
        dept_id: extract_for_department(markdown, dept_id)
        for dept_id in KNOWN_DEPARTMENTS
    }
    unknown = find_unknown_departments(markdown)
    open_questions: list[str] = []
    if unknown:
        open_questions.append(
            "RFP mentions department(s) outside HealthCore intake map "
            f"({', '.join(unknown)}); route via Revenue Cycle — do not invent workers."
        )
    if not metadata.get("covered_population"):
        open_questions.append(
            "Covered population / volume not found in the RFP; Revenue/Clinical must clarify."
        )
    return {
        "departments": list(KNOWN_DEPARTMENTS),
        "workstreams": workstreams,
        "unknown_departments": unknown,
        "open_questions": open_questions,
    }
