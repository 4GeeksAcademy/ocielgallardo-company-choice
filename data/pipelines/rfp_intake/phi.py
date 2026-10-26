"""Lightweight PHI detection + redaction for RFP intake (HIPAA / UK GDPR).

Heuristic only for Part 1 — never invent patient data; never persist raw matches.
"""

from __future__ import annotations

import re
from typing import Any

# Patterns that strongly suggest individual patient identifiers / clinical notes.
_PHI_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?i:patient|mr\.|mrs\.|ms\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",
    ),
    re.compile(
        r"\b(?:diagnosis|diagnosed with|medical record|MRN|SSN|date of birth|DOB)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:clinical case summary|case summary for)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?i:patient\s+name|full\s+name)\s*[:\-]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",
    ),
    re.compile(
        r"\b(?:ICD-?10|ICD-?9)\s*[:=]?\s*[A-Z]\d{2}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:nhs\s+number|national\s+insurance)\b",
        re.IGNORECASE,
    ),
)

_REDACTION = "[REDACTED_PHI]"


def detect_and_redact_phi(text: str) -> dict[str, Any]:
    """Return redacted text and whether PHI-like content was found."""
    if not text:
        return {"text": text, "contains_phi": False, "match_count": 0}

    redacted = text
    match_count = 0
    for pattern in _PHI_PATTERNS:
        matches = list(pattern.finditer(redacted))
        if not matches:
            continue
        match_count += len(matches)
        redacted = pattern.sub(_REDACTION, redacted)

    return {
        "text": redacted,
        "contains_phi": match_count > 0,
        "match_count": match_count,
    }
