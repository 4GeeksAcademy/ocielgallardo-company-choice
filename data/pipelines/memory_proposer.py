"""Structured LLM calls for the agent-memory loop (self-eval + confirmation).

Responsibility: the two small structured decisions the memory flow needs on
top of the answer itself —

1. ``classify_decision`` — when a proposal is pending, classify the user's
   next message against it with an explicit label (``approve`` | ``reject``
   | ``edit`` | ``unrelated``). Anything outside the catalogue, and any
   ambiguous or topic-changing message, maps to ``unrelated`` which the
   caller resolves as **rejected by default** — never approval by silence.
2. ``propose_from_interaction`` — self-evaluation for answer paths whose
   final text is deterministic (tool answers): one structured call that
   returns a memory proposal or ``None``.

The RAG/hybrid paths do not use ``propose_from_interaction``: there the
answer and the proposal already come from the single structured generation
call (``data.pipelines.rag.generate_answer_with_proposal``), so the
interaction still costs exactly one model call.

Every function here degrades safely: no credentials, a transport error or
unparseable output means "no proposal" / "unrelated" (→ default rejection),
never a crash and never a silent approval.
"""

from __future__ import annotations

import json
import logging
import re

from data.pipelines.agent_memory import CATEGORIES

logger = logging.getLogger(__name__)

DECISION_LABELS = ("approve", "reject", "edit", "unrelated")

# Prompt-side category vocabulary (kept aligned with agent_memory.CATEGORIES).
_CATEGORIES_HINT = ", ".join(CATEGORIES)

SELF_EVAL_RULES = """
You also self-evaluate the interaction for agent memory.

Propose a memory ONLY when this conversation produced a NEW or CORRECTED
durable operational fact that will matter in a future conversation
(for example: a recurring clinic-hours change, a supplier delivery day, a
local procedure exception, a known incident pattern without patient data, a
staff member's presentation preference).

Do NOT propose anything for: one-off data lookups (the answer lives in a
dashboard or system of record), conversation closings or thanks, translation
or formatting tasks, or anything that only matters to this single exchange.
When in doubt, return null — silence is the safe default.

NEVER put patient-identifying or clinical information in a proposal (HIPAA
+ UK GDPR): no patient names, record numbers, dates of birth, insurance or
government IDs, diagnoses, lab results, prescriptions or clinical notes.
If the user asks you to remember such content, refuse in the answer and
return null.

Use "scope" for the clinic name (or "network" when it is not clinic-specific)
and one of these categories: {categories}.

Output JSON only: {{"answer": "<the user-facing answer>",
"propuesta_memoria": null or {{"scope": "...", "category": "...",
"fact": "...", "reason": "..."}}}}
""".format(categories=_CATEGORIES_HINT)

DECISION_RULES = """
A memory proposal is pending. Classify the user's message against that
proposal — do not answer the message, only classify it.

Labels:
- "approve": the user clearly accepts the proposal as proposed
  (for example: "sí", "sí, guárdalo", "yes", "store it", "sounds right").
- "reject": the user clearly refuses it ("no", "no lo guardes", "don't").
- "edit": the user accepts in spirit but changes a detail — return the
  corrected fact in "edited_fact".
- "unrelated": anything else — a new question, small talk, thanks, or any
  ambiguous phrasing that does not clearly approve or reject.

Rules:
- Never treat silence, a changed topic, or vague wording as approval.
- When in doubt, use "unrelated" (the system discards the proposal).
- The proposal text is operational fact text; classify only, never extend it.

Output JSON only: {{"label": "approve|reject|edit|unrelated",
"edited_fact": null or "corrected fact text"}}
"""

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text or "").strip()


def chat_json(system_prompt: str, user_prompt: str, *, max_tokens: int = 700) -> str:
    """One JSON-mode chat call (Groq/OpenAI-compatible). Raises on failure."""
    from openai import OpenAI

    from data.process.rag import RagSettings

    settings = RagSettings.from_env()
    if not settings.llm_model:
        raise RuntimeError(
            "LLM_MODEL is not set. Add the 4Geeks-provided generation model ID to .env."
        )
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not set. Add it to .env (gitignored).")
    client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_api_url)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        completion = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # provider/model without json mode support
        logger.warning("json response_format unsupported (%s); retrying plain", exc)
        completion = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens,
        )
    return (completion.choices[0].message.content or "").strip()


def parse_json_object(text: str) -> dict | None:
    cleaned = _strip_fences(text)
    if not cleaned:
        return None
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            payload = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return payload if isinstance(payload, dict) else None


def normalize_proposal(raw: object) -> dict | None:
    """Validate/shape a model proposal; ``None`` when there is nothing to ask."""
    if not isinstance(raw, dict):
        return None
    fact = str(raw.get("fact") or "").strip()
    if not fact:
        return None
    return {
        "scope": str(raw.get("scope") or "network").strip() or "network",
        "category": str(raw.get("category") or "other").strip() or "other",
        "fact": fact[:500],
        "reason": str(raw.get("reason") or "").strip()[:500],
    }


def normalize_decision(raw: object) -> dict:
    """Map model output to a safe decision; anything doubtful → unrelated."""
    if not isinstance(raw, dict):
        return {"label": "unrelated", "edited_fact": None}
    label = str(raw.get("label") or "").strip().lower()
    if label not in DECISION_LABELS:
        return {"label": "unrelated", "edited_fact": None}
    edited = raw.get("edited_fact")
    edited_fact = str(edited).strip()[:500] if isinstance(edited, str) else None
    if label == "edit" and not edited_fact:
        return {"label": "unrelated", "edited_fact": None}
    return {"label": label, "edited_fact": edited_fact or None}


def propose_from_interaction(question: str, answer: str) -> dict | None:
    """Self-evaluate a deterministic (tool) answer for a memory proposal."""
    prompt = (
        f"Coordinator question:\n{question}\n\n"
        f"Agent answer:\n{answer}\n\n"
        "Return the JSON described in the instructions."
    )
    try:
        raw = parse_json_object(chat_json(SELF_EVAL_RULES, prompt))
    except Exception as exc:
        logger.warning("memory self-evaluation unavailable: %s", exc)
        return None
    if raw is None:
        return None
    return normalize_proposal(raw.get("propuesta_memoria"))


def classify_decision(proposal: dict, message: str) -> dict:
    """Classify the user's message against the pending proposal."""
    prompt = (
        f"Pending proposal:\n"
        f"- scope: {proposal.get('scope', '')}\n"
        f"- category: {proposal.get('category', '')}\n"
        f"- fact: {proposal.get('fact', '')}\n"
        f"- reason: {proposal.get('reason', '')}\n\n"
        f"User message:\n{message}\n\n"
        "Return the JSON described in the instructions."
    )
    try:
        raw = parse_json_object(chat_json(DECISION_RULES, prompt))
    except Exception as exc:
        logger.warning("memory decision classification unavailable: %s", exc)
        return {"label": "unrelated", "edited_fact": None}
    if raw is None:
        return {"label": "unrelated", "edited_fact": None}
    return normalize_decision(raw)
