"""Scope guardrails for the HealthCore support agent (hito 26 Part 2).

Responsibility: keep the agent inside the HealthCore clinic domain — the
harness layer that turns a raw LLM into a reliable company assistant
(ticket SEC-114). Three independent layers, each covering a different
failure mode (a single filter is not an acceptable control):

1. **Structural** — malformed classifier output degrades to ``domain``
   (the hardened SYSTEM_PROMPT is the backstop), never a crash and never
   a silent jailbreak win.
2. **Content / security (deterministic)** — ``detect_jailbreak`` and
   ``detect_personal_task`` are regex screens run *before* any LLM call.
   A jailbreak attempt never reaches the model; a personal-task request is
   refused with a fixed bilingual message.
3. **Content (model-assisted)** — ``classify_intent`` is a small
   structured call (same pattern as ``memory_proposer``) that labels the
   remaining messages ``domain | casual | personal_task``. On transport
   failure or unparseable output it degrades to ``domain`` so normal
   clinic questions keep working; the prompt-level scope rules in
   ``data.pipelines.rag.SYSTEM_PROMPT`` contain anything that slips
   through.

Decision contract (``evaluate_scope``):

======================  =========================================
Input                   Decision
======================  =========================================
HealthCore domain       ``domain`` → normal RAG / tool routing
Casual / trivia         ``casual`` → short redirect (LLM + fallback)
Personal task ajeno     ``personal_task`` → firm refusal, no task
Jailbreak / injection   ``jailbreak`` → firm refusal, no LLM, no task
======================  =========================================

Reason *codes* only in verdicts and spans (stable audit contract, same
discipline as ``memory_phi_guard``). Matched text is never returned.
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from data.pipelines import agent_content_guard

logger = logging.getLogger(__name__)

DECISIONS = ("domain", "casual", "personal_task", "jailbreak")

# --- Deterministic screens (layer 2): run before any LLM call ---

# Prompt-injection / instruction-override attempts, EN + ES. Patterns are
# deliberately specific ("ignore your instructions", not the bare word
# "instructions") so legitimate clinic questions do not false-positive.
_JAILBREAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:ignore|disregard|override|forget|bypass)\b.{0,40}\b"
        r"(?:your|the|all|any|previous|prior|above|earlier|initial|"
        r"original|system)\b.{0,20}\b"
        r"(?:instructions?|rules?|prompts?|directives?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:ignore|disregard|override|forget)\b\s+(?:all\s+)?"
        r"(?:instructions?|rules?|prompts?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bact\s+(?:as\s+)?(?:if|like)\b.{0,40}\b"
        r"(?:no|without|not\s+bound|unrestricted|free)\b.{0,20}\b"
        r"(?:rules?|restrictions?|instructions?|limits?|guardrails?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byou\s+are\s+(?:now\s+)?(?:DAN|Dan|jailbroken|unrestricted)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:developer|sudo|god|admin|debug)\s+mode\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:reveal|show|print|repeat|display|leak)\b.{0,30}\b"
        r"(?:your|the|this)\b.{0,20}\b"
        r"(?:system\s+prompt|hidden\s+prompt|initial\s+prompt|"
        r"system\s+instructions?|reglas?\s+internas?|"
        r"prompt\s+del\s+sistema|instrucciones?\s+del\s+sistema)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bnew\s+instructions?\s*:",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdo\s+anything\s+now\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:ignore|disregard|ignora(?:r)?|olvida(?:r)?)\b.{0,40}\b"
        r"(?:tus|las|todas|estas|anteriores|previas|del\s+sistema)\b.{0,20}\b"
        r"(?:instrucciones?|reglas?|directivas?|lineamientos?|"
        r"restricciones?|l[íi]mites?|órdenes?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bolvida(?:r)?\b.{0,40}\b"
        r"(?:tus|las|todas|estas|anteriores|previas|del\s+sistema)\b.{0,20}\b"
        r"(?:instrucciones?|reglas?|directivas?|lineamientos?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bact[úu]a\b.{0,30}\bcomo\s+si\b.{0,40}\b"
        r"(?:no|sin)\b.{0,20}\b"
        r"(?:tuvieras?|tienes?|hubiera|existieran)\b.{0,20}\b"
        r"(?:reglas?|instrucciones?|restricciones?|limites?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"eres\s+ahora\s+(?:DAN|Dan|libre|sin\s+reglas)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bmodo\s+(?:desarrollador|developer|sudo|god|admin)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"mu[ée]strame\b.{0,30}\b"
        r"(?:tu|el|la|las|tus)\b.{0,20}\b"
        r"(?:prompt|instrucciones?|reglas?|directivas?|configuraci[óo]n)\b"
        r"(?:\s+del\s+sistema)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"revela(?:r)?\b.{0,30}\b"
        r"(?:tu|el|la|las|tus)\b.{0,20}\b"
        r"(?:prompt|instrucciones?|reglas?\s+internas?|"
        r"prompt\s+del\s+sistema)\b",
        re.IGNORECASE,
    ),
)

# Personal, non-HealthCore deliverables: essays, homework, personal code,
# therapy, etc. Careful not to match clinic billing "coding" or policy
# "documentation" questions.
_PERSONAL_TASK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bwrite\b(?:\s+\w+){0,3}\s+"
        r"(?:an?\s+)?(?:essay|poem|poetry|song|lyrics|story|novel|"
        r"blog\s+post|cover\s+letter|cv|resume|speech|monologue)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:do|finish|help\s+me\s+with)\s+my\s+"
        r"(?:homework|essay|paper|thesis|dissertation|assignment|"
        r"school\s+project)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:my|our)\s+(?:own|personal|private|side)\s+"
        r"(?:project|app|application|website|startup|business|blog|code)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwrite\b(?:\s+\w+){0,2}\s+"
        r"(?:code|a\s+script|a\s+function|a\s+class|a\s+program|"
        r"python|javascript|java|react|html|css|sql)\b"
        r"(?:\s+\w+){0,4}\s+(?:for|to|in)\s+(?:my|our)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:fix|debug|review)\s+my\s+"
        r"(?:code|bug|script|project|repo|repository)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:therapy|therapist|counselling|counseling|"
        r"mental\s+health\s+(?:advice|support)|"
        r"relationship\s+advice|life\s+coaching)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:cita|sesi[óo]n)\s+con\s+(?:el\s+|la\s+)?"
        r"(?:psic[óo]log[oa]|terapeuta|terapeuta)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bpersonal\s+(?:advice|counselling|counseling|email|letter|"
        r"finance|finances|investment|diet|workout)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:escri\w*|escr[íi]\w*)\b(?:\s+\w+){0,3}\s+"
        r"(?:un\s+)?(?:ensayo|poema|canci[óo]n|historia|novela|"
        r"correo\s+personal|carta\s+personal|cv|curr[ií]culum)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bhazme\b(?:\s+\w+){0,2}\s+"
        r"(?:la\s+)?(?:tarea|deberes|ensayo|redacci[óo]n)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bescribe(?:r)?\s+c[óo]digo\b(?:\s+\w+){0,4}\s+"
        r"(?:para|de)\s+(?:mi|nuestro)\b",
        re.IGNORECASE,
    ),
)

MAX_SCAN_CHARS = 4000


class ScopeVerdict(BaseModel):
    """Result of screening one user message for agent scope."""

    decision: str = "domain"
    reasons: list[str] = Field(default_factory=list)
    classifier_used: bool = False

    @property
    def is_refusal(self) -> bool:
        return self.decision in ("jailbreak", "personal_task")


def detect_jailbreak(text: str | None) -> list[str]:
    """Return reason codes for instruction-override / jailbreak patterns."""
    if not text:
        return []
    haystack = text[:MAX_SCAN_CHARS]
    reasons: list[str] = []
    for index, pattern in enumerate(_JAILBREAK_PATTERNS):
        if pattern.search(haystack):
            code = f"injection_pattern_{index}"
            if code not in reasons:
                reasons.append(code)
    return reasons


def detect_personal_task(text: str | None) -> list[str]:
    """Return reason codes for off-domain personal-task patterns."""
    if not text:
        return []
    haystack = text[:MAX_SCAN_CHARS]
    reasons: list[str] = []
    for index, pattern in enumerate(_PERSONAL_TASK_PATTERNS):
        if pattern.search(haystack):
            code = f"personal_task_pattern_{index}"
            if code not in reasons:
                reasons.append(code)
    return reasons


# --- Model-assisted intent classifier (layer 3) ---

INTENT_LABELS = ("domain", "casual", "personal_task")

INTENT_RULES = """\
You classify one user message for the HealthCore clinic knowledge assistant.
The assistant only serves HealthCore clinic operations (policies, \
appointments, insurance questions, referrals, tickets/incidents, inventory, \
HIPAA/UK GDPR operational procedures, staffing logistics).

Labels:
- "domain": a question or request about HealthCore clinics, their policies, \
appointments, billing/insurance coverage, referrals, tickets, inventory, \
compliance procedures, or staff operational workflows — including short \
follow-ups ("yes", "what about the UK?") in that context.
- "casual": brief small talk, greeting, thanks, or general trivia with NO \
deliverable requested (for example "hello", "thanks!", "what's the capital \
of France?", "tell me a joke").
- "personal_task": a request for work unrelated to HealthCore — writing \
essays, poems, emails, or homework; coding for a personal project; therapy \
or personal advice; anything the assistant should refuse as a general-
purpose assistant.

Rules:
- Prefer "domain" when the message plausibly concerns clinic operations.
- Never invent a fourth label. When in doubt between casual and domain, \
use "domain".

Output JSON only: {"intent": "domain|casual|personal_task"}"""


def classify_intent(question: str) -> str:
    """Structured intent label; degrades to ``domain`` on any failure.

    Transport errors, missing credentials and unparseable model output all
    return ``domain`` so legitimate clinic questions keep flowing — the
    hardened SYSTEM_PROMPT and the deterministic screens remain the
    backstop for anything the classifier would have caught.
    """
    from data.pipelines import memory_proposer

    prompt = (
        f"User message:\n{question}\n\n"
        "Return the JSON described in the instructions."
    )
    try:
        raw = memory_proposer.chat_json(INTENT_RULES, prompt, max_tokens=64)
    except Exception as exc:
        logger.warning("scope intent classification unavailable: %s", exc)
        return "domain"
    payload = memory_proposer.parse_json_object(raw)
    if payload is None:
        return "domain"
    intent = str(payload.get("intent") or "").strip().lower()
    return intent if intent in INTENT_LABELS else "domain"


def evaluate_scope(question: str) -> ScopeVerdict:
    """Full scope pipeline for one message (deterministic screens → classifier).

    Order matters: the regex screens short-circuit *before* any model call,
    so a jailbreak never reaches the LLM (security) and the classifier only
    spends a call on messages that need disambiguation.

    Every non-domain decision is a guardrail activation: it is counted and
    logged with its ``failure_type`` (``security`` for jailbreak, ``content``
    for personal-task blocks and casual redirects).
    """
    text = (question or "").strip()
    if not text:
        return ScopeVerdict(decision="domain", reasons=["blank"])

    jailbreak_reasons = detect_jailbreak(text)
    if jailbreak_reasons:
        verdict = ScopeVerdict(decision="jailbreak", reasons=jailbreak_reasons)
        _record_scope_activation(verdict)
        return verdict

    personal_reasons = detect_personal_task(text)
    if personal_reasons:
        verdict = ScopeVerdict(
            decision="personal_task", reasons=personal_reasons
        )
        _record_scope_activation(verdict)
        return verdict

    intent = classify_intent(text)
    if intent == "personal_task":
        verdict = ScopeVerdict(
            decision="personal_task",
            reasons=["classifier_personal_task"],
            classifier_used=True,
        )
        _record_scope_activation(verdict)
        return verdict
    if intent == "casual":
        verdict = ScopeVerdict(
            decision="casual",
            reasons=["classifier_casual"],
            classifier_used=True,
        )
        _record_scope_activation(verdict)
        return verdict
    return ScopeVerdict(decision="domain", reasons=[], classifier_used=True)


def scope_failure_type(decision: str) -> str:
    """Failure taxonomy for one scope decision (SEC-114 observability)."""
    if decision == "jailbreak":
        return agent_content_guard.FAILURE_SECURITY
    if decision in ("personal_task", "casual"):
        return agent_content_guard.FAILURE_CONTENT
    return agent_content_guard.FAILURE_STRUCTURAL


def _record_scope_activation(verdict: ScopeVerdict) -> None:
    """Count + log one scope block/redirect (never echoes matched text)."""
    event = "scope_blocked" if verdict.is_refusal else "scope_redirected"
    failure_type = scope_failure_type(verdict.decision)
    agent_content_guard.record_activation(event, failure_type)
    logger.warning(
        "guardrail %s decision=%s failure_type=%s reasons=%s classifier_used=%s",
        event,
        verdict.decision,
        failure_type,
        verdict.reasons,
        verdict.classifier_used,
    )


# --- User-facing messages (deterministic, bilingual) ---

JAILBREAK_REFUSAL_EN = (
    "I can't change my instructions or ignore the rules I run under. "
    "I'm the HealthCore clinic knowledge assistant — ask me about clinic "
    "policies, appointments, tickets, or inventory and I'll be glad to help."
)

JAILBREAK_REFUSAL_ES = (
    "No puedo cambiar mis instrucciones ni ignorar las reglas con las que "
    "opero. Soy el asistente de conocimiento de las clínicas HealthCore: "
    "pregúntame sobre políticas de la clínica, citas, tickets o inventario "
    "y con gusto te ayudo."
)

PERSONAL_TASK_REFUSAL_EN = (
    "I can only help with HealthCore clinic work — policies, appointments, "
    "insurance questions, tickets, and inventory. I can't write essays, "
    "code for personal projects, or provide personal advice. Is there "
    "something about the clinics I can help with?"
)

PERSONAL_TASK_REFUSAL_ES = (
    "Solo puedo ayudar con el trabajo de las clínicas HealthCore — "
    "políticas, citas, seguros, tickets e inventario. No puedo escribir "
    "ensayos, código para proyectos personales ni dar consejos personales. "
    "¿Hay algo de las clínicas en lo que pueda ayudarte?"
)

CASUAL_FALLBACK_EN = (
    "Happy to help with HealthCore clinic topics — policies, appointments, "
    "insurance, tickets, or inventory. What would you like to know?"
)

CASUAL_FALLBACK_ES = (
    "Con gusto te ayudo con temas de las clínicas HealthCore: políticas, "
    "citas, seguros, tickets o inventario. ¿Qué te gustaría saber?"
)

CASUAL_REDIRECT_SYSTEM_PROMPT = (
    "You are the HealthCore clinic knowledge assistant. The user made "
    "casual small talk or asked general trivia. Reply with ONE short "
    "sentence (maximum two) that briefly acknowledges the message and "
    "redirects to HealthCore clinic topics: policies, appointments, "
    "insurance, tickets, or inventory. Never answer the general-knowledge "
    "question in full. Never write essays, code, poems, or personal "
    "advice. No emoji. Reply in the user's language."
)

_ES_CASUAL_MARKERS = (
    " el ",
    " la ",
    " los ",
    " las ",
    " un ",
    " una ",
    " de ",
    " del ",
    " en ",
    " que ",
    " con ",
    " por ",
    " para ",
    " se ",
    " no ",
    " tus ",
    " tu ",
    " mis ",
    " hola",
    " gracias",
    " por favor",
    " qué ",
    " cómo ",
    " clínica",
    " clinica",
    " cita",
    " política",
    " politica",
    " inventario",
    " ticket",
    " instrucciones",
    " reglas",
    " escríbeme",
    " escribeme",
    " ensayo",
    " poema",
    " tarea",
)


def is_spanish_message(text: str) -> bool:
    """Tiny language heuristic so canned messages follow the user's language."""
    probe = f" {(text or '').lower()} "
    return sum(1 for marker in _ES_CASUAL_MARKERS if marker in probe) >= 2


def refusal_message(decision: str, question: str = "") -> str:
    """Canonical bilingual refusal for ``jailbreak`` / ``personal_task``."""
    spanish = is_spanish_message(question)
    if decision == "jailbreak":
        return JAILBREAK_REFUSAL_ES if spanish else JAILBREAK_REFUSAL_EN
    return PERSONAL_TASK_REFUSAL_ES if spanish else PERSONAL_TASK_REFUSAL_EN


def generate_casual_redirect(question: str) -> str:
    """One constrained LLM call: a short acknowledge + HealthCore redirect.

    Falls back to a canned bilingual template when the model is
    unavailable or returns nothing usable, so a casual message never
    crashes the run and never becomes a general-purpose answer.
    """
    from openai import OpenAI

    from data.process.rag import RagSettings

    settings = RagSettings.from_env()
    fallback = (
        CASUAL_FALLBACK_ES
        if is_spanish_message(question)
        else CASUAL_FALLBACK_EN
    )
    if not settings.llm_model or not settings.llm_api_key:
        return fallback
    try:
        client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)
        completion = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": CASUAL_REDIRECT_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0.2,
            max_tokens=80,
        )
        text = (completion.choices[0].message.content or "").strip()
        return text or fallback
    except Exception:
        logger.warning("casual redirect generation failed; using canned fallback")
        return fallback
