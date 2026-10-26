"""Classifier agent: is this a legitimate HealthCore institutional RFP?"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from data.pipelines.rfp_intake.llm import chat_json

_RFP_POSITIVE = re.compile(
    r"\b(?:request\s+for\s+proposal|rfp|proposal\s+request|"
    r"seeking\s+(?:a\s+)?(?:proposal|partner|partnership)|"
    r"occupational\s+health|corporate\s+wellness|referral\s+network|"
    r"would\s+like\s+to\s+(?:engage|partner)|"
    r"employees?\s+covered|students?\s+covered)\b",
    re.IGNORECASE,
)

_VENDOR_NEGATIVE = re.compile(
    r"\b(?:our\s+(?:ehr|emr)\s+system|vendor\s+pitch|we\s+sell|"
    r"buy\s+our\s+(?:software|platform|ehr)|demo\s+our\s+product|"
    r"electronic\s+health\s+record\s+solution\s+for\s+sale|"
    r"replace\s+your\s+(?:ehr|emr))\b",
    re.IGNORECASE,
)


@dataclass
class ClassificationResult:
    is_rfp: bool
    reason: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_rfp": self.is_rfp,
            "reason": self.reason,
            "confidence": self.confidence,
        }


def classify_rfp_heuristic(markdown: str) -> ClassificationResult:
    """Deterministic classifier used in tests and as LLM fallback."""
    text = markdown or ""
    vendor_hits = len(_VENDOR_NEGATIVE.findall(text))
    rfp_hits = len(_RFP_POSITIVE.findall(text))

    # Explicit vendor pitch without client-RFP framing → reject.
    if vendor_hits > 0 and rfp_hits == 0:
        return ClassificationResult(
            is_rfp=False,
            reason="Document reads as a vendor product pitch, not a client RFP.",
            confidence=0.9,
        )
    if vendor_hits > rfp_hits and vendor_hits >= 2:
        return ClassificationResult(
            is_rfp=False,
            reason="Strong vendor-sales language outweighs RFP signals.",
            confidence=0.85,
        )
    if rfp_hits > 0:
        return ClassificationResult(
            is_rfp=True,
            reason="Institutional request signals detected (program / coverage / RFP language).",
            confidence=min(0.95, 0.55 + 0.1 * rfp_hits),
        )
    # Informal RFPs may look like emails — accept mild partnership asks.
    if re.search(r"\b(?:partnership|satellite clinic|referral)\b", text, re.I):
        return ClassificationResult(
            is_rfp=True,
            reason="Informal partnership / referral request treated as institutional RFP.",
            confidence=0.7,
        )
    return ClassificationResult(
        is_rfp=False,
        reason="No clear institutional RFP or partnership request signals.",
        confidence=0.6,
    )


def classify_rfp(markdown: str) -> ClassificationResult:
    """Classify with optional LLM; always falls back to heuristics."""
    heuristic = classify_rfp_heuristic(markdown)
    llm = chat_json(
        system=(
            "You classify documents for HealthCore. A valid RFP is a client "
            "request for occupational health, corporate wellness, or referral "
            "network partnership (formal RFP or informal email). Vendor pitches "
            "selling EHR/software to HealthCore are NOT RFPs. "
            "Respond JSON: {is_rfp: bool, reason: string, confidence: number 0-1}."
        ),
        user=markdown[:12000],
    )
    if not llm:
        return heuristic
    try:
        is_rfp = bool(llm.get("is_rfp"))
        reason = str(llm.get("reason") or heuristic.reason)
        confidence = float(llm.get("confidence", heuristic.confidence))
        # Prefer reject when both agree on vendor; prefer accept when heuristic is strong accept.
        if heuristic.is_rfp and heuristic.confidence >= 0.85 and not is_rfp:
            return heuristic
        if (not heuristic.is_rfp) and heuristic.confidence >= 0.85 and is_rfp:
            return heuristic
        return ClassificationResult(is_rfp=is_rfp, reason=reason, confidence=confidence)
    except (TypeError, ValueError):
        return heuristic
