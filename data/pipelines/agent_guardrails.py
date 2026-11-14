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

# Personal identifiers / clinical details of one specific patient. On their
# own these words are harmless ("What documents does a new patient need to
# bring?", "What is the clinic's phone number?"); combined with a reference
# to a specific patient or a ticket they are a PHI request and are refused
# BEFORE any ticket/stock tool or the knowledge base runs.
_PHI_ATTRIBUTE_RE = re.compile(
    r"\b(?:(?:home|postal|mailing|street)\s+)?address(?:es)?\b|\bwhere\s+(?:does|do)\b.{0,40}\blives?\b"
    r"|\bphone(?:\s*(?:number|no\.?|#))?\b|\b(?:tele)?phone\b|\bmobile(?:\s+number)?\b"
    r"|\bcell(?:\s*phone|\s+number)\b|\bcontact\s+(?:details|info(?:rmation)?|number)\b"
    r"|\be-?mail(?:\s+address)?\b|\bdate\s+of\s+birth\b|\bd\.?o\.?b\.?\b|\bbirth\s*(?:day|date)\b"
    r"|\bdiagnos(?:is|es|ed)\b|\bmrn\b|\binsurance\s+(?:id|number|policy\s+number)\b"
    r"|\bdirecci[oó]n\b|\bdomicilio\b|\btel[eé]fono\b|\bm[oó]vil\b|\bcorreo(?:\s+electr[oó]nico)?\b"
    r"|\bfecha\s+de\s+nacimiento\b|\bdiagn[oó]stico\b",
    re.IGNORECASE | re.DOTALL,
)
# Clinical details: refused only for a named/numbered patient, never just
# because a ticket number is present ("Is ticket 8 a medication error?").
_PHI_CLINICAL_RE = re.compile(
    r"\bmedical\s+(?:history|record|condition)s?\b|\bprescriptions?\b"
    r"|\bmedications?\b|\bhistorial\s+m[eé]dico\b|\bmedicaci[oó]n\b",
    re.IGNORECASE,
)
# A specific patient: "this/that patient", "the patient's", "of/for the
# patient", "patient 123", "patient MRN-42", "the patient in ticket 8",
# "del paciente", or a ticket/incident number. A bare "the patient" in a
# policy question ("Do we need the patient date of birth on the form?") is
# not enough on its own.
_SPECIFIC_PATIENT_RE = re.compile(
    r"\b(?:this|that|said|his|her|their|este|ese|esta|esa)\s+(?:patient|paciente)\b"
    r"|\b(?:the|a)\s+patient's\b"
    r"|\b(?:of|for|from|about|del|de\s+la|de\s+este|de\s+ese)\s+(?:the\s+)?"
    r"(?:patient|paciente)\b(?!s)"
    r"|\b(?:patient|paciente)\s*(?:#|no\.?|number|id|n[uú]mero)?\s*[A-Z]{0,4}-?\d+\b"
    r"|\b(?:patient|paciente)(?:'s)?\s+(?:in|on|from|of|for|en|del?)\s+"
    r"(?:the\s+|el\s+)?(?:ticket|incident|case|caso|incidencia)\b",
    re.IGNORECASE,
)
_TICKET_NUMBER_RE = re.compile(
    r"\b(?:ticket|incident|caso|incidencia)\s*#?\s*\d+\b", re.IGNORECASE
)
# "patient John" / "patient Smith's": a capitalised name right after
# "patient" (case-sensitive on purpose so "patient need" is not a name).
_NAMED_PATIENT_RE = re.compile(r"\b[Pp](?:atient|aciente)\s+[A-Z][a-z]+")


def asks_for_patient_phi(question: str) -> bool:
    """True when the question asks for a specific patient's identifiers/PHI.

    "What's the home address of the patient in ticket 8?" -> True;
    "What is the status of ticket 8?" / "What documents does a new patient
    need to bring?" -> False.
    """
    text = (question or "").strip()
    if not text:
        return False
    specific_patient = bool(
        _SPECIFIC_PATIENT_RE.search(text) or _NAMED_PATIENT_RE.search(text)
    )
    if _PHI_ATTRIBUTE_RE.search(text):
        return specific_patient or bool(_TICKET_NUMBER_RE.search(text))
    return specific_patient and bool(_PHI_CLINICAL_RE.search(text))


# Extra output patterns for synthetic SSN-like tokens (demo fixtures only).
_OUTPUT_SSN_LIKE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


_PHI_EXFIL_PATTERNS: tuple[re.Pattern[str], ...] = _INJECTION_PATTERNS[2:]


def is_prompt_injection_or_phi_exfil(question: str) -> bool:
    """True when the question looks like a jailbreak or PHI exfil attempt."""
    text = (question or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS) or (
        asks_for_patient_phi(text)
    )


def is_phi_exfil_attempt(question: str) -> bool:
    """True when the question looks like a PHI/identifier exfiltration attempt.

    Jailbreak phrasing without identifier/PHI probes is handled by the Hito 26
    scope harness (``scope_check``), so this stays focused on exfil patterns.
    """
    text = (question or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _PHI_EXFIL_PATTERNS) or (
        asks_for_patient_phi(text)
    )


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
