"""Content isolation + output validation + guardrail observability (Part 2).

Three responsibilities the harness needs beyond the scope guard
(``agent_scope_guard``), covering rubric gaps from the SEC-114 review:

1. **External-content isolation** — ``sanitize_context_chunk`` /
   ``sanitize_tool_text`` screen text that arrives from RAG documents or
   external tools *before* it is placed in a prompt or rendered into an
   answer. Retrieved/tool content is **data, never instructions**: any
   instruction-like pattern inside it is neutralized (reason codes only).
2. **Output validation** — ``validate_output`` runs on the final answer
   before it reaches the user: empty/structural failures, leakage of
   internal prompt markers, and PHI-like content (via the existing
   ``memory_phi_guard`` screen) all produce a safe replacement answer.
3. **Observability** — every guardrail activation (scope blocks,
   redirects, content sanitization, output rejections) is counted with a
   ``failure_type`` of ``structural`` | ``content`` | ``security`` and can
   be summarized via ``get_activation_summary()`` or the CLI.

This module intentionally does **not** import ``agent_scope_guard``
(the scope guard imports the counters from here — one-way dependency).
"""

from __future__ import annotations

import logging
import re
import threading
from collections import Counter
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from data.pipelines import memory_phi_guard

logger = logging.getLogger(__name__)

# Failure taxonomy (shared with the scope guard and the evidence doc).
FAILURE_STRUCTURAL = "structural"
FAILURE_CONTENT = "content"
FAILURE_SECURITY = "security"

# --- Guardrail activation counters (in-process, thread-safe) ---

_lock = threading.Lock()
_activations: Counter[tuple[str, str]] = Counter()  # (event, failure_type)


def record_activation(event: str, failure_type: str) -> None:
    """Count one guardrail activation (event name + failure taxonomy)."""
    with _lock:
        _activations[(event, failure_type)] += 1


def get_activation_summary() -> dict[str, dict[str, int]]:
    """Snapshot: ``{event: {failure_type: count}}`` (sorted, copy)."""
    with _lock:
        snapshot = dict(_activations)
    summary: dict[str, dict[str, int]] = {}
    for (event, failure_type), count in sorted(snapshot.items()):
        summary.setdefault(event, {})[failure_type] = count
    return summary


def reset_activations() -> None:
    """Clear counters (tests / demo sessions)."""
    with _lock:
        _activations.clear()


# --- Instruction-like patterns *inside* external content ---

# A retrieved document or tool payload must never carry instructions. These
# patterns are the content-isolation screen (distinct from the user-input
# jailbreak screen in ``agent_scope_guard``): they fire on text the *system*
# retrieved, not on what the user typed.
_CONTENT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:ignore|disregard|override|forget|bypass)\b.{0,40}\b"
        r"(?:your|the|all|any|previous|prior|above|system|initial)\b.{0,20}\b"
        r"(?:instructions?|rules?|prompts?|directives?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:you\s+are\s+now|act\s+as\s+if)\b.{0,40}\b"
        r"(?:DAN|unrestricted|no\s+rules|without\s+rules)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bnew\s+instructions?\s*:",
        re.IGNORECASE,
    ),
    re.compile(
        r"ignora(?:r)?\b.{0,40}\b"
        r"(?:tus|las|todas|las\s+anteriores|del\s+sistema)\b.{0,20}\b"
        r"(?:instrucciones?|reglas?|directivas?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"olvida(?:r)?\b.{0,40}\b"
        r"(?:tus|las|todas|del\s+sistema)\b.{0,20}\b"
        r"(?:instrucciones?|reglas?)\b",
        re.IGNORECASE,
    ),
)

# Internal prompt markers that must never appear in a user-facing answer
# (leakage of the harness prompt = structural/security failure).
_INTERNAL_MARKER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bHard rules:"),
    re.compile(r"\bScope rules \(non-negotiable\)"),
    re.compile(r"\bRetrieved policy context:"),
    re.compile(r"\bCoordinator question:"),
    re.compile(r"\bpropuesta_memoria\b"),
    re.compile(r"\bSYSTEM_PROMPT\b"),
    re.compile(r"\bSELF_EVAL_RULES\b"),
    re.compile(r"\bINTENT_RULES\b"),
    re.compile(r"You are the knowledge assistant for HealthCore patient coordinators"),
)

MAX_SCAN_CHARS = 4000

_NEUTRALIZED_SEGMENT = "[content removed: instruction-like text in retrieved data]"


# --- External-content isolation ---


@dataclass(frozen=True)
class SanitizedText:
    """Result of screening one external text fragment."""

    text: str
    reasons: list[str] = field(default_factory=list)

    @property
    def was_sanitized(self) -> bool:
        return bool(self.reasons)


def detect_content_injection(text: str | None) -> list[str]:
    """Reason codes for instruction-like patterns inside external content."""
    if not text:
        return []
    haystack = text[:MAX_SCAN_CHARS]
    reasons: list[str] = []
    for index, pattern in enumerate(_CONTENT_INJECTION_PATTERNS):
        if pattern.search(haystack):
            code = f"external_injection_{index}"
            if code not in reasons:
                reasons.append(code)
    return reasons


def sanitize_external_text(text: str | None) -> SanitizedText:
    """Neutralize instruction-like segments inside retrieved/tool text.

    Detected segments are replaced with a fixed placeholder (fail-closed):
    the surrounding factual content is kept so a poisoned chunk cannot
    erase legitimate policy text, but the injection never reaches the model
    as an instruction. Reason codes only — matched text is not echoed.
    """
    if not text:
        return SanitizedText(text or "")
    reasons = detect_content_injection(text)
    if not reasons:
        return SanitizedText(text=text)
    # Line-level neutralization: drop only the lines that screen positive.
    lines = text.splitlines()
    kept: list[str] = []
    for line in lines:
        if detect_content_injection(line):
            kept.append(_NEUTRALIZED_SEGMENT)
        else:
            kept.append(line)
    sanitized = "\n".join(kept)
    # If every line was positive or the whole blob matched without newlines,
    # fall back to replacing the entire haystack.
    if _NEUTRALIZED_SEGMENT not in sanitized:
        sanitized = _NEUTRALIZED_SEGMENT
    record_activation("content_sanitized", FAILURE_SECURITY)
    logger.warning(
        "guardrail content_sanitized failure_type=%s reasons=%s",
        FAILURE_SECURITY,
        reasons,
    )
    return SanitizedText(text=sanitized, reasons=reasons)


def sanitize_context_chunk(chunk: dict) -> dict:
    """Sanitize one RAG payload dict in place-safe fashion (returns a copy)."""
    if not isinstance(chunk, dict):
        return chunk
    cleaned = dict(chunk)
    original = str(cleaned.get("text") or "")
    result = sanitize_external_text(original)
    cleaned["text"] = result.text
    if result.reasons:
        cleaned["content_guard"] = result.reasons
    return cleaned


def sanitize_tool_text(text: str | None) -> str:
    """Sanitize a free-text field from an external tool payload."""
    return sanitize_external_text(text).text


# --- Output validation (before the answer reaches the user) ---

OUTPUT_FALLBACK_EN = (
    "I can't share that response. Please ask again about HealthCore clinic "
    "topics — policies, appointments, insurance, tickets, or inventory."
)

OUTPUT_FALLBACK_ES = (
    "No puedo compartir esa respuesta. Pregunta de nuevo sobre temas de las "
    "clínicas HealthCore: políticas, citas, seguros, tickets o inventario."
)

_EMPTY_FALLBACK = (
    "I don't have enough information in the clinic policies to answer that. "
    "Please verify it with billing or the clinic front desk."
)


class OutputVerdict(BaseModel):
    """Result of validating one final answer before delivery."""

    allowed: bool = True
    reasons: list[str] = Field(default_factory=list)
    safe_answer: str = ""
    failure_type: str | None = None


def detect_internal_leak(answer: str | None) -> list[str]:
    """Reason codes when the answer exposes internal prompt markers."""
    if not answer:
        return []
    haystack = answer[:MAX_SCAN_CHARS]
    reasons: list[str] = []
    for index, pattern in enumerate(_INTERNAL_MARKER_PATTERNS):
        if pattern.search(haystack):
            code = f"internal_marker_{index}"
            if code not in reasons:
                reasons.append(code)
    return reasons


def validate_output(answer: str | None) -> OutputVerdict:
    """Screen the final answer: structure, internal leaks, PHI-like content.

    Fail-closed: any hit replaces the answer with a safe bilingual fallback
    (never echoing the rejected text, because the rejected text may itself
    be PHI or a leaked secret). Activation is counted and logged with its
    ``failure_type``.
    """
    text = (answer or "").strip()
    if not text:
        record_activation("output_rejected", FAILURE_STRUCTURAL)
        logger.warning(
            "guardrail output_rejected failure_type=%s reasons=%s",
            FAILURE_STRUCTURAL,
            ["empty_answer"],
        )
        return OutputVerdict(
            allowed=False,
            reasons=["empty_answer"],
            safe_answer=_EMPTY_FALLBACK,
            failure_type=FAILURE_STRUCTURAL,
        )

    leak_reasons = detect_internal_leak(text)
    if leak_reasons:
        record_activation("output_rejected", FAILURE_SECURITY)
        logger.warning(
            "guardrail output_rejected failure_type=%s reasons=%s",
            FAILURE_SECURITY,
            leak_reasons,
        )
        return OutputVerdict(
            allowed=False,
            reasons=leak_reasons,
            safe_answer=OUTPUT_FALLBACK_EN,
            failure_type=FAILURE_SECURITY,
        )

    phi_verdict = memory_phi_guard.scan(text)
    if not phi_verdict.allowed:
        record_activation("output_rejected", FAILURE_CONTENT)
        logger.warning(
            "guardrail output_rejected failure_type=%s reasons=%s",
            FAILURE_CONTENT,
            phi_verdict.reasons,
        )
        return OutputVerdict(
            allowed=False,
            reasons=list(phi_verdict.reasons),
            safe_answer=OUTPUT_FALLBACK_EN,
            failure_type=FAILURE_CONTENT,
        )

    return OutputVerdict(allowed=True, safe_answer=text)


# --- CLI: activation summary after a test/demo session ---


def _main(argv: list[str] | None = None) -> int:
    import json
    import sys

    args = list(argv if argv is not None else sys.argv[1:])
    command = (args[0] if args else "summary").strip().lower()
    if command == "summary":
        summary = get_activation_summary()
        total = sum(
            count for event in summary.values() for count in event.values()
        )
        print(json.dumps({"activations": summary, "total": total}, indent=2))
        return 0
    print("Usage: python -m data.pipelines.agent_content_guard [summary]")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
