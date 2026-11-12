"""Input/output guardrails for the staff knowledge / compliance agent.

Blocks jailbreak + PHI-exfiltration prompts before the LLM runs, and
refuses model outputs that look like PHI. Uses only synthetic patterns —
never log or store identifiable patient content.
"""

from __future__ import annotations

import re

from data.pipelines.rfp_intake.phi import detect_and_redact_phi

SECURITY_REFUSAL_ANSWER = (
    "I cannot help with that request. HealthCore assistants only answer "
    "staff policy questions from the knowledge base and never disclose "
    "patient identifiers or protected health information."
)

# Jailbreak / instruction-override + credential/PHI exfil heuristics.
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bignore\b.{0,40}\b(polic(?:y|ies)|instructions?|rules?|system\s*prompt)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(disregard|override)\b.{0,40}\b(previous|prior|system)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(social\s*security|ssn|nhs\s*number|national\s*insurance)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(tell\s+me|give\s+me|reveal|exfiltrate)\b.{0,60}\b"
        r"(patient|ssn|social\s*security|medical\s*record|mrn)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bpatient\s+[A-Z]{0,4}-?\d{2,}\b",
        re.IGNORECASE,
    ),
)

# Extra output patterns for synthetic SSN-like tokens (demo fixtures only).
_OUTPUT_SSN_LIKE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


_PHI_EXFIL_PATTERNS: tuple[re.Pattern[str], ...] = _INJECTION_PATTERNS[2:]


def is_prompt_injection_or_phi_exfil(question: str) -> bool:
    """True when the question looks like a jailbreak or PHI exfil attempt."""
    text = (question or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)


def is_phi_exfil_attempt(question: str) -> bool:
    """True when the question looks like a PHI/identifier exfiltration attempt.

    Jailbreak phrasing without identifier/PHI probes is handled by the Hito 26
    scope harness (``scope_check``), so this stays focused on exfil patterns.
    """
    text = (question or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _PHI_EXFIL_PATTERNS)


def sanitize_agent_output(answer: str) -> str:
    """Refuse or redact answers that appear to contain PHI-like content."""
    text = answer or ""
    if not text.strip():
        return text
    if _OUTPUT_SSN_LIKE.search(text):
        return SECURITY_REFUSAL_ANSWER
    result = detect_and_redact_phi(text)
    if result.get("contains_phi"):
        return SECURITY_REFUSAL_ANSWER
    return text
