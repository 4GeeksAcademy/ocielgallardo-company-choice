"""Deterministic PHI screen for agent-memory proposals (HIPAA + UK GDPR).

HealthCore's briefing makes this non-negotiable: no patient identifier or
clinical content may ever enter the agent's memory — not as an approved
entry, not as a proposal shown to the user, not in an audit record. The LLM
is instructed to never emit PHI, but instructions alone are not a control,
so every candidate memory text is screened here:

1. before a proposal is shown to the user (``record_proposal``),
2. before an edited proposal is stored,
3. again on every consolidated version before it is written back.

The guard returns reason *codes* only. Matched text is never returned,
logged or persisted, because the matched text may itself be PHI. The screen
is a deterministic best-effort filter (regex + keyword heuristics), not a
certified de-identification engine: it is layered on top of the model
prompt rules and fails closed (anything detected blocks the write).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

# Reason codes (stable contract for audit records and user-facing refusals).
PHI_REASONS = (
    "patient_name",
    "record_number",
    "date_of_birth",
    "government_id",
    "insurance_id",
    "clinical_content",
    "long_identifier",
)


class PhiVerdict(BaseModel):
    """Result of screening a candidate memory text."""

    allowed: bool = True
    reasons: list[str] = Field(default_factory=list)


# "patient Johnson" / "paciente Smith" — with a lookahead so operational
# phrasing like "Patient not informed of appointment reschedule" (a real
# incident title) does not read as a patient name.
_PATIENT_NAME_RE = re.compile(
    r"\b(?:patient|Patient)\s+"
    r"(?!(?:was|is|are|were|has|have|had|not|needs?|can|cannot|will|must|"
    r"records?|data|information|privacy|care|portal|education|scheduling|"
    r"rights|consent|satisfaction|experience|no)\b)"
    r"[A-Z][\w'’\-]+"
    r"|\b(?:el paciente|la paciente|paciente)\s+"
    r"(?!(?:fue|es|está|estaba|no|necesita|tiene|será|debe|ha|han|hay|un|una)\b)"
    r"[A-Z][\w'’\-]+"
)

_RECORD_NUMBER_RE = re.compile(
    r"\b(?:MRN|medical\s+record(?:\s+(?:number|no\.?|#))?|"
    r"historia\s+cl[íi]nica|n[úu]mero\s+de\s+historia)\s*#?\s*[A-Z0-9][\w-]{2,}",
    re.IGNORECASE,
)

_DOB_RE = re.compile(
    r"\b(?:DOB|date\s+of\s+birth|fecha\s+de\s+naci(?:miento|ement))\s*[:#-]?\s*\S+",
    re.IGNORECASE,
)

_GOVERNMENT_ID_RE = re.compile(
    r"\b(?:SSN|social\s+security(?:\s+number)?|NHS\s+number|"
    r"national\s+insurance\s+(?:number|no\.?)|"
    r"n[úu]mero\s+de\s+seguridad\s+social)\s*#?\s*[\w-]{4,}",
    re.IGNORECASE,
)

_INSURANCE_ID_RE = re.compile(
    r"\b(?:insurance|member|policy|subscriber|asegurad[oa])\s*"
    r"(?:number|no\.?|#|id|n[úu]mero)?\s*#?\s*[A-Z]{0,3}[-\s]?\d{5,}\b",
    re.IGNORECASE,
)

_CLINICAL_CONTENT_RE = re.compile(
    r"\b(?:lab(?:oratory)?\s+results?|test\s+results?|"
    r"resultados?\s+de\s+laboratorio|"
    r"clinical\s+notes?|notas?\s+cl[íi]nicas?|"
    r"prescription|prescripci[óo]n|receta médica|"
    r"diagnos(?:is|tic(?:s|ed)?)|diagn[óo]stico|"
    r"symptoms?|s[íi]ntomas|"
    r"vital\s+signs?|signos\s+vitales|"
    r"icd[- ]?10)\b",
    re.IGNORECASE,
)

# Unlabelled 9+ digit runs (candidate MRN / insurance / member numbers).
# Ticket ids and SKUs in this system are far shorter, so this stays safe.
_LONG_IDENTIFIER_RE = re.compile(r"\b\d{9,}\b")

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("patient_name", _PATIENT_NAME_RE),
    ("record_number", _RECORD_NUMBER_RE),
    ("date_of_birth", _DOB_RE),
    ("government_id", _GOVERNMENT_ID_RE),
    ("insurance_id", _INSURANCE_ID_RE),
    ("clinical_content", _CLINICAL_CONTENT_RE),
    ("long_identifier", _LONG_IDENTIFIER_RE),
)

MAX_SCAN_CHARS = 4000


def scan(text: str | None) -> PhiVerdict:
    """Screen ``text`` for patient-identifying or clinical content.

    Returns ``allowed=False`` with one reason code per matching rule. Codes
    only — the matched snippet is discarded immediately and must never be
    stored or logged by callers.
    """
    if not text:
        return PhiVerdict(allowed=True)
    haystack = text[:MAX_SCAN_CHARS]
    reasons: list[str] = []
    for reason, pattern in _PATTERNS:
        if reason in reasons:
            continue
        if pattern.search(haystack):
            reasons.append(reason)
    return PhiVerdict(allowed=not reasons, reasons=reasons)


def scan_proposal(proposal: dict) -> PhiVerdict:
    """Screen every text field of a memory proposal (merged verdict)."""
    parts = [
        str(proposal.get("scope") or ""),
        str(proposal.get("category") or ""),
        str(proposal.get("fact") or ""),
        str(proposal.get("reason") or ""),
        str(proposal.get("edited_fact") or ""),
    ]
    verdict = scan(" \n ".join(parts))
    return verdict


PHI_REFUSAL_EN = (
    "\n\nI can't save that to my memory: it looks like it contains patient-"
    "identifying or clinical information (HIPAA / UK GDPR). Nothing was "
    "stored. Operational facts without patient data are fine to remember."
)

PHI_REFUSAL_ES = (
    "\n\nNo puedo guardar eso en mi memoria: parece contener información "
    "identificable de un paciente o contenido clínico (HIPAA / UK GDPR). "
    "No se guardó nada. Los hechos operativos sin datos de pacientes sí "
    "se pueden recordar."
)
