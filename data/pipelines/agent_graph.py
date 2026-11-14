"""HealthCore support agent as an explicit LangGraph (Part 2).

Responsibility: route each coordinator question to the right source —
stable knowledge via RAG (``retrieve`` + ``generate_answer``), live tickets
and stock via the MCP server tools — with
single-responsibility nodes, conditional routing, minimal state, per-run
traces, and checkpointing.

Node contract (binding):
- ``receive_node`` normalizes the question only (no retrieval, no LLM, no tools).
- ``scope_check_node`` screens the message for agent scope (jailbreak /
  personal task / casual / domain) via ``agent_scope_guard.evaluate_scope``.
- ``scope_refusal_node`` returns the fixed bilingual refusal for jailbreak /
  personal-task messages (no LLM, no tools, no memory proposal).
- ``casual_redirect_node`` answers casual small talk with one constrained
  LLM call (canned bilingual fallback) that redirects to HealthCore topics.
- ``decide_route_node`` classifies RAG vs incidents vs inventory vs hybrid.
- ``retrieve_node`` calls ONLY ``retrieve(question)``; retrieved chunks pass
  ``agent_content_guard.sanitize_context_chunk`` (external content is data,
  never instructions).
- ``generate_node`` calls ONLY ``generate_answer(question, context)``.
- ``lookup_incident_node`` / ``lookup_inventory_node`` call ONLY their
  MCP tool (MCP is the single transport — no direct HTTP fallback; never RAG,
  never each other).
- ``answer_from_tool_node`` surfaces successful tool data deterministically.
- ``synthesize_hybrid_node`` prefixes the deterministic tool fact block and
  appends the LLM policy paragraph (tool facts are never left to the model).
- ``tool_fallback_node`` answers honestly when a tool fails (no invented state).
- ``refuse_node`` / ``honest_node`` keep the Part 1 blank/empty-context paths.
- No node imports or calls the monolithic ``query()``.

Memory (Hito 26, orchestrated by :func:`run_agent` around the graph, so the
node/span contract above stays stable):

1. any **pending proposal** for the session is resolved first — classified
   against the incoming message (``approve``/``reject``/``edit``/``unrelated``;
   silence or ambiguity = rejected by default) and written to the audit trail;
2. approved facts relevant to the question are injected as ``memory_context``
   (explicit ``agent:memory`` store, never the RAG collections);
3. the answer-producing paths return answer + ``propuesta_memoria`` from a
   **single structured call** (``generate_answer_with_proposal``); tool-only
   paths self-evaluate with one structured call;
4. a proposal is shown to the user inside the same answer (question at the
   end) only after the PHI screen passes — otherwise the user gets an explicit
   HIPAA/UK GDPR refusal and nothing is stored.

The graph is compiled at import time (with a ``MemorySaver`` checkpointer) so
structural errors fail fast. Services call :func:`run_agent` and read
``result["answer"]`` — HTTP still returns ``{question, answer}`` only.

Run a question locally:
    uv run python -m data.pipelines.agent_graph "what is the status of ticket 2?"
"""

from __future__ import annotations

import contextvars
import logging
import re
import sys
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from data.pipelines import (
    agent_content_guard,
    agent_memory,
    agent_scope_guard,
    inventory_search,
    mcp_client,
    memory_phi_guard,
    memory_proposer,
    rag as rag_pipeline,
)
from data.pipelines.agent_tools import (
    INCIDENT_TOOL_FALLBACK,
    INVENTORY_TOOL_FALLBACK,
    IncidentToolInput,
    InventoryToolInput,
    format_incident_answer,
    format_inventory_answer,
    format_rfp_answer,
)

logger = logging.getLogger(__name__)

# Ticket / incident phrasing that must not go to the policy RAG alone.
_TICKET_ID_RE = re.compile(
    r"\b(?:ticket|incident|caso|incidencia)\s*#?\s*(\d+)\b",
    re.IGNORECASE,
)
_TICKET_STATUS_RE = re.compile(
    r"\b(?:status|estado|state)\b.*\b(?:ticket|incident|caso|incidencia)\b"
    r"|\b(?:ticket|incident|caso|incidencia)\b.*\b(?:status|estado|state)\b",
    re.IGNORECASE,
)
_INCIDENT_KEYWORDS_RE = re.compile(
    r"\b(?:open tickets?|tickets? abiertos?|incident manager|"
    r"gestor de incidentes|support ticket)\b",
    re.IGNORECASE,
)
# "latest / last / most recent ticket" (EN + ES) — no id needed.
_LATEST_RE = re.compile(
    r"\b(?:latest|last|most\s+recent|newest|recent|[uú]ltim[oa]s?|"
    r"m[aá]s\s+recientes?)\b",
    re.IGNORECASE,
)
_TICKET_NOUN_RE = re.compile(
    r"\b(?:tickets?|incidents?|casos?|incidencias?|rfps?)\b", re.IGNORECASE
)
_RFP_RE = re.compile(r"\brfps?\b|\brequests?\s+for\s+proposals?\b", re.IGNORECASE)
# Words that map a question onto an incident category / status filter.
_CATEGORY_KEYWORDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bbilling|\bfactura", re.IGNORECASE), "billing_error"),
    # "IT" is matched case-sensitively so "is it open?" is not a category.
    (re.compile(r"\bIT\b|\b[Ss]ystems?\b|\b[Ss]oftware\b|\b[Ss]istemas?\b"), "it_system"),
    (re.compile(r"\bequipment|\bequipo|\bdevice", re.IGNORECASE), "clinical_equipment"),
    (re.compile(r"\bcompliance|\bcumplimiento|\bbreach", re.IGNORECASE), "compliance_breach"),
    (re.compile(r"\bpatient experience|\bexperiencia", re.IGNORECASE), "patient_experience"),
    (re.compile(r"\bstaff\b", re.IGNORECASE), "staff_issue"),
    (re.compile(r"\bfacilit|\binstalaci", re.IGNORECASE), "facility_issue"),
    (re.compile(r"\breferral|\bderivaci", re.IGNORECASE), "referral_issue"),
)
_STATUS_KEYWORDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bin[\s_-]progress\b|\ben curso\b", re.IGNORECASE), "in_progress"),
    (re.compile(r"\bopen\b|\babiert[oa]s?\b", re.IGNORECASE), "open"),
    (re.compile(r"\bresolved\b|\bclosed\b|\bresuelt[oa]s?\b", re.IGNORECASE), "resolved"),
    (re.compile(r"\bdiscarded\b|\bdescartad[oa]s?\b", re.IGNORECASE), "discarded"),
)
_SKU_RE = re.compile(r"\b(HCR-[A-Z]+-\d+)\b", re.IGNORECASE)
_INVENTORY_KEYWORDS_RE = re.compile(
    r"\b(?:stock|inventory|inventario|suministro|supply|supplies|"
    r"do we have|tenemos stock|hay stock|cu[aá]nto stock)\b",
    re.IGNORECASE,
)
# Quantity phrasing (EN + ES) that marks a stock question when it also names
# a supply we stock: "¿Cuántos guantes de nitrilo quedan?", "How many gloves
# are left?". Kept separate from the keywords above so "¿Cuántos días hay
# para cancelar?" never reaches the inventory tool.
_STOCK_QUANTITY_RE = re.compile(
    r"\b(?:cu[aá]nt[oa]s?|quedan?|hay|how\s+many|how\s+much|left|remaining)\b",
    re.IGNORECASE,
)
# Policy/procedure phrasing that, combined with a live tool signal, is hybrid.
_POLICY_SIGNAL_RE = re.compile(
    r"\b(?:polic(?:y|ies)|procedure|procedimiento|pol[ií]tica|"
    r"cancel(?:lation|ling)?|fee|cargo|coverage|insurance|seguro|"
    r"hipaa|gdpr|appointment|cita|referral|document(?:s|ation)?|"
    r"what do i need|according to|seg[uú]n (?:la |el )?|"
    r"no-?show|medicare|medicaid)\b",
    re.IGNORECASE,
)


class AgentState(TypedDict):
    """State travelling between nodes. Tools add route + tool_result only.

    Memory fields are set by ``run_agent`` orchestration: ``session_id``
    scopes the pending proposal, ``memory_context`` holds the approved facts
    relevant to this question, ``proposal`` carries the candidate memory
    emitted by the single structured generation call (empty when none).
    Scope fields are set by ``scope_check_node``
    (``domain|casual|personal_task|jailbreak`` + reason codes).
    """

    question: str
    context: list[dict]
    answer: str
    route: str
    tool_result: dict
    sources_used: list[str]
    session_id: str
    memory_context: list[dict]
    proposal: dict
    scope_decision: str
    scope_reasons: list[str]


DEFAULT_MEMORY_SESSION = "default"

PROPOSAL_QUESTION_ES = (
    "\n\n¿Quieres que recuerde esto para la próxima vez? Responde sí, "
    "no o corrígeme."
)
PROPOSAL_QUESTION_EN = (
    "\n\nDo you want me to remember this for next time? Reply yes, no, "
    "or correct me."
)

_SAVENOTE_ES = "\n\nGuardado en mi memoria."
_SAVENOTE_EN = "\n\nSaved to my memory."
_REJECTNOTE_ES = "\n\nEntendido, no lo guardaré."
_REJECTNOTE_EN = "\n\nUnderstood — I won't store it."

# Clean, standalone replies to "Do you want me to remember this?". When the
# user's message is only that decision, the agent answers with one of these
# and does NOT run the question through the graph (no generic greeting).
MEMORY_SAVED_EN = "Got it, I saved that for next time."
MEMORY_SAVED_ES = "Entendido, lo he guardado para la próxima vez."
MEMORY_EDITED_EN = "Got it, I saved your corrected version for next time."
MEMORY_EDITED_ES = "Entendido, he guardado tu versión corregida para la próxima vez."
MEMORY_REJECTED_EN = "Understood, I won't save it."
MEMORY_REJECTED_ES = "Entendido, no lo guardaré."
MEMORY_ASK_CORRECTION_EN = (
    "Sure, tell me the correct version and I'll save that instead."
)
MEMORY_ASK_CORRECTION_ES = (
    "Claro, dime la versión correcta y guardaré esa en su lugar."
)

_MEMORY_REPLY_STRIP_RE = re.compile(r"[¡!¿?.,;:—–\-\"()]+")
_MEMORY_APPROVE_KEYS = frozenset(
    "yes yeah yep yup sure ok okay save remember store keep "
    "sí si vale claro guárdalo guardalo guarda guárdala recuérdalo recuerdalo "
    "recuerda".split()  # noqa: SIM905 - word list kept readable
)
_MEMORY_REJECT_KEYS = frozenset(
    "no nope don't dont not never forget olvídalo olvidalo".split()  # noqa: SIM905
)
_MEMORY_FILLER = frozenset(
    "please thanks thank you that it this for next time the a do please "
    "go ahead lo eso esto para la próxima proxima vez por favor gracias "
    "store save remember keep guardes recuerdes need i".split()  # noqa: SIM905
)
_MEMORY_CORRECT_RE = re.compile(
    r"^\s*(?:(?:please|por favor)\s*,?\s*)?"
    r"(?:correct\s+(?:me|it|that)|i(?:'d| would)?\s+(?:like|want)\s+to\s+correct"
    r"(?:\s+(?:it|that))?|let\s+me\s+correct(?:\s+(?:it|that))?|"
    r"corr[ií]geme|corr[ií]gelo|quiero\s+corregir(?:lo)?)"
    r"\s*(?:,?\s*(?:please|por favor))?\s*[.!]?\s*$",
    re.IGNORECASE,
)


def bare_memory_reply(message: str) -> str | None:
    """``approve`` / ``reject`` / ``correct`` when the message is only that.

    "Yes, save that for next time." -> approve; "No, don't store that." ->
    reject; "correct me" -> correct. Anything carrying another request
    ("yes, and what is the fee?") returns ``None`` and goes through the
    normal classification + answer path.
    """
    text = (message or "").strip()
    if not text or len(text) > 80:
        return None
    if _MEMORY_CORRECT_RE.match(text):
        return "correct"
    if "?" in text or "¿" in text:
        return None
    words = _MEMORY_REPLY_STRIP_RE.sub(" ", text.lower().replace("’", "'")).split()
    if not words:
        return None
    vocabulary = _MEMORY_APPROVE_KEYS | _MEMORY_REJECT_KEYS | _MEMORY_FILLER
    if any(word not in vocabulary for word in words):
        return None
    has_reject = any(word in _MEMORY_REJECT_KEYS for word in words)
    has_approve = any(word in _MEMORY_APPROVE_KEYS for word in words)
    if has_reject:
        # "no, don't save it" is a rejection; "yes … no" is ambiguous.
        if any(word in {"yes", "yeah", "yep", "yup", "sure", "sí", "si", "vale", "claro"}
               for word in words):
            return None
        return "reject"
    if has_approve:
        return "approve"
    return None


_ES_MARKERS = (
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
    " sí,",
    " sí ",
    "gracias",
    "por favor",
    "cómo",
    "cuándo",
    "próxima",
    "clínica",
    "paciente",
    "recuerda",
    "guardar",
    "guarda",
)


def _is_spanish(text: str) -> bool:
    """Tiny language heuristic so memory prompts follow the user's language."""
    probe = f" {(text or '').lower()} "
    return sum(1 for marker in _ES_MARKERS if marker in probe) >= 2


# --- Internal per-run trace store (queryable, bounded, no PHI beyond the question) ---

_MAX_TRACES = 100
_TRACES: OrderedDict[str, dict] = OrderedDict()
_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "agent_graph_trace_id", default=None
)


def _record_span(
    node: str, started_at: float, finished_at: float, output: dict | None = None
) -> None:
    trace_id = _current_trace_id.get()
    if trace_id is None:
        return
    trace = _TRACES.get(trace_id)
    if trace is None:
        return
    trace["spans"].append(
        {
            "node": node,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": round((finished_at - started_at) * 1000, 2),
            "output": output or {},
        }
    )


def get_trace(trace_id: str) -> dict | None:
    """Return the stored trace for ``trace_id`` (copy), or ``None``."""
    trace = _TRACES.get(trace_id)
    return dict(trace) if trace is not None else None


def get_last_trace() -> dict | None:
    """Return the most recent stored trace (copy), or ``None``."""
    if not _TRACES:
        return None
    return dict(next(reversed(_TRACES.values())))


def get_agent_state(trace_id: str) -> dict | None:
    """Return the checkpointed graph state for a past run, or ``None``."""
    try:
        snapshot = graph.get_state({"configurable": {"thread_id": trace_id}})
    except Exception:
        logger.exception("Could not read checkpoint for run %s", trace_id)
        return None
    if not snapshot.values:
        return None
    return dict(snapshot.values)


def _store_trace(trace: dict) -> None:
    _TRACES[trace["trace_id"]] = trace
    while len(_TRACES) > _MAX_TRACES:
        _TRACES.popitem(last=False)


def extract_ticket_id(question: str) -> int | None:
    """Return the first ticket/incident id mentioned in ``question``, if any."""
    match = _TICKET_ID_RE.search(question or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def asks_for_latest_ticket(question: str) -> bool:
    """True for "latest/last/most recent ticket|incident|RFP" questions."""
    text = question or ""
    return bool(_LATEST_RE.search(text)) and bool(_TICKET_NOUN_RE.search(text))


def mentions_rfp(question: str) -> bool:
    """True when the question is about RFP tickets (not incident tickets)."""
    return bool(_RFP_RE.search(question or ""))


def extract_incident_filters(question: str) -> dict[str, str]:
    """Category / status filters named in a "latest ticket" question."""
    text = question or ""
    filters: dict[str, str] = {}
    for pattern, category in _CATEGORY_KEYWORDS:
        if pattern.search(text):
            filters["category"] = category
            break
    for pattern, status in _STATUS_KEYWORDS:
        if pattern.search(text):
            filters["status"] = status
            break
    return filters


def extract_sku(question: str) -> str | None:
    """Return the first HealthCore SKU mentioned in ``question``, if any."""
    match = _SKU_RE.search(question or "")
    return match.group(1).upper() if match else None


# Filler words (EN/ES) dropped from stock questions so only the product terms
# reach the inventory tool ("How many gloves do we have in stock?" -> "gloves").
_INVENTORY_STOPWORDS = frozenset(
    """
    a an the of in on at for to is are was be do does did we you i our us my
    have has any how many much what which there left remaining available units unit
    please can could tell me show check level levels current currently right now
    el la los las un una unos unas de del al en con para por es son hay que
    qué cual cuál cuales cuáles cuanto cuánto cuanta cuánta cuantos cuántos
    cuantas cuántas tenemos tiene tienen queda quedan nos me dime muestra
    nivel niveles actual ahora disponible disponibles unidades unidad y o
    """.split()  # noqa: SIM905 - word list kept readable
)


def extract_inventory_name_query(question: str) -> str | None:
    """Best-effort product name terms for stock questions without a SKU."""
    if extract_sku(question or ""):
        return None
    cleaned = _INVENTORY_KEYWORDS_RE.sub(" ", question or "")
    cleaned = re.sub(r"[¿?¡!.,;:\"'()]", " ", cleaned)
    words = [
        word
        for word in cleaned.split()
        if word.lower() not in _INVENTORY_STOPWORDS
    ]
    return " ".join(words) or None


def has_policy_signal(question: str) -> bool:
    """True when the question also asks about stable policy/procedure knowledge."""
    return bool(_POLICY_SIGNAL_RE.search(question or ""))


def _needs_incident_tool(text: str) -> bool:
    return (
        extract_ticket_id(text) is not None
        or asks_for_latest_ticket(text)
        or bool(_TICKET_STATUS_RE.search(text))
        or bool(_INCIDENT_KEYWORDS_RE.search(text))
    )


def asks_stock_by_quantity(text: str) -> bool:
    """"How many / cuántos / quedan / hay" + a supply noun, without policy words."""
    return (
        bool(_STOCK_QUANTITY_RE.search(text or ""))
        and inventory_search.mentions_product_noun(text or "")
        and not has_policy_signal(text or "")
    )


def _needs_inventory_tool(text: str) -> bool:
    return (
        extract_sku(text) is not None
        or bool(_INVENTORY_KEYWORDS_RE.search(text))
        or asks_stock_by_quantity(text)
    )


def classify_route(
    question: str,
) -> Literal[
    "refuse",
    "incidents",
    "inventory",
    "hybrid_incidents",
    "hybrid_inventory",
    "rag",
]:
    """Decide source(s) from the question alone (no user-specified source)."""
    text = (question or "").strip()
    if not text:
        return "refuse"
    policy = has_policy_signal(text)
    # Incidents before inventory: ticket ids must never be confused with stock.
    if _needs_incident_tool(text):
        return "hybrid_incidents" if policy else "incidents"
    if _needs_inventory_tool(text):
        return "hybrid_inventory" if policy else "inventory"
    return "rag"


def is_hybrid_route(route: str | None) -> bool:
    """True for routes that combine a live tool with RAG in one run."""
    return bool(route) and str(route).startswith("hybrid_")


# --- Nodes: one responsibility each ---


def receive_node(state: AgentState) -> dict:
    """Normalize the incoming question (strip whitespace). No I/O."""
    started = time.time()
    question = ""
    try:
        question = state["question"].strip()
        return {"question": question}
    finally:
        _record_span(
            "receive", started, time.time(), {"question_chars": len(question)}
        )


def scope_check_node(state: AgentState) -> dict:
    """Screen the message for agent scope (SEC-114 harness).

    Deterministic jailbreak/personal-task screens run before any LLM call;
    the model-assisted intent classifier only runs on the remainder.
    """
    started = time.time()
    decision = "domain"
    reasons: list[str] = []
    try:
        verdict = agent_scope_guard.evaluate_scope(state["question"])
        decision = verdict.decision
        reasons = list(verdict.reasons)
        return {"scope_decision": decision, "scope_reasons": reasons}
    finally:
        _record_span(
            "scope_check",
            started,
            time.time(),
            {
                "scope_decision": decision,
                "scope_reasons": reasons,
                "failure_type": (
                    agent_scope_guard.scope_failure_type(decision)
                    if decision != "domain"
                    else None
                ),
            },
        )


def scope_refusal_node(state: AgentState) -> dict:
    """Fixed bilingual refusal for jailbreak / personal-task messages.

    No LLM, no tools, no memory proposal — the task is never performed and
    the system prompt is never revealed or changed.
    """
    started = time.time()
    decision = state.get("scope_decision") or "personal_task"
    failure_type = agent_scope_guard.scope_failure_type(decision)
    answer = ""
    try:
        answer = agent_scope_guard.refusal_message(
            decision, state["question"]
        )
        return {"answer": answer}
    finally:
        _record_span(
            "scope_refusal",
            started,
            time.time(),
            {
                "scope_decision": decision,
                "failure_type": failure_type,
                "answer_chars": len(answer),
                "route": "scope_refusal",
            },
        )


def casual_redirect_node(state: AgentState) -> dict:
    """Answer casual small talk with one constrained LLM call + redirect.

    Canned bilingual fallback when the model is unavailable so a greeting
    never crashes the run and never becomes a general-purpose answer.
    """
    started = time.time()
    answer = ""
    used_fallback = False
    try:
        answer = agent_scope_guard.generate_casual_redirect(state["question"])
        used_fallback = answer in (
            agent_scope_guard.CASUAL_FALLBACK_EN,
            agent_scope_guard.CASUAL_FALLBACK_ES,
        )
        return {"answer": answer}
    finally:
        _record_span(
            "casual_redirect",
            started,
            time.time(),
            {
                "answer_chars": len(answer),
                "used_fallback": used_fallback,
                "failure_type": agent_content_guard.FAILURE_CONTENT,
                "route": "scope_casual",
            },
        )


def decide_route_node(state: AgentState) -> dict:
    """Classify which source(s) the question needs: RAG, tool, or both."""
    started = time.time()
    route = "rag"
    ticket_id: int | None = None
    sku: str | None = None
    try:
        route = classify_route(state["question"])
        ticket_id = extract_ticket_id(state["question"])
        sku = extract_sku(state["question"])
        return {"route": route}
    finally:
        _record_span(
            "decide_route",
            started,
            time.time(),
            {"route": route, "ticket_id": ticket_id, "sku": sku},
        )


def retrieve_node(state: AgentState) -> dict:
    """Retrieve policy chunks for ``state['question']`` via ``retrieve()``.

    Every retrieved chunk passes the content-isolation guard: instruction-
    like text *inside a document* is data, never a system instruction, and
    is neutralized before it can reach the prompt.
    """
    started = time.time()
    context: list[dict] = []
    sanitized_hits = 0
    try:
        context = [
            agent_content_guard.sanitize_context_chunk(chunk)
            for chunk in rag_pipeline.retrieve(state["question"])
        ]
        sanitized_hits = sum(
            1 for chunk in context if chunk.get("content_guard")
        )
        sources = list(state.get("sources_used") or [])
        if "rag" not in sources:
            sources = [*sources, "rag"]
        return {"context": context, "sources_used": sources}
    finally:
        _record_span(
            "retrieve",
            started,
            time.time(),
            {
                "n_chunks": len(context),
                "sources": sorted(
                    {str(chunk.get("source_document", "")) for chunk in context}
                ),
                "source_kind": "rag",
                "content_sanitized": sanitized_hits,
                "hybrid": is_hybrid_route(state.get("route")),
            },
        )


def generate_node(state: AgentState) -> dict:
    """Generate the answer from ``question`` + already-retrieved ``context``.

    Single structured call: the answer the user sees plus an optional memory
    proposal field (self-evaluation rides on the same call).
    """
    started = time.time()
    answer = ""
    proposal: dict | None = None
    try:
        answer, proposal = rag_pipeline.generate_answer_with_proposal(
            state["question"],
            state["context"],
            memory=state.get("memory_context") or [],
        )
        return {"answer": answer, "proposal": proposal or {}}
    finally:
        _record_span(
            "generate",
            started,
            time.time(),
            {"answer_chars": len(answer), "has_proposal": bool(proposal)},
        )


def refuse_node(state: AgentState) -> dict:
    """Answer a blank question honestly without retrieval or LLM."""
    started = time.time()
    try:
        return {"answer": rag_pipeline.INSUFFICIENT_INFO_ANSWER}
    finally:
        _record_span("refuse", started, time.time(), {"reason": "blank_question"})


def refuse_security_node(state: AgentState) -> dict:
    """Refuse jailbreak / PHI-exfil prompts without calling the LLM."""
    from data.pipelines.agent_guardrails import SECURITY_REFUSAL_ANSWER

    started = time.time()
    try:
        return {"answer": SECURITY_REFUSAL_ANSWER}
    finally:
        _record_span(
            "refuse_security",
            started,
            time.time(),
            {"reason": "prompt_injection_or_phi_exfil"},
        )


def honest_node(state: AgentState) -> dict:
    """Answer empty retrieval honestly via the existing empty-context path.

    Same single structured call as ``generate`` — answer plus memory field.
    """
    started = time.time()
    answer = ""
    proposal: dict | None = None
    try:
        answer, proposal = rag_pipeline.generate_answer_with_proposal(
            state["question"],
            [],
            memory=state.get("memory_context") or [],
        )
        return {"answer": answer, "proposal": proposal or {}}
    finally:
        _record_span(
            "honest",
            started,
            time.time(),
            {"answer_chars": len(answer), "has_proposal": bool(proposal)},
        )


def lookup_incident_node(state: AgentState) -> dict:
    """Call the incidents (or RFP) tool over MCP (the only transport).

    - ``ticket 8`` -> ``get_incident_status``;
    - ``latest RFP`` / an RFP question without an incident id ->
      ``get_latest_rfp_ticket``;
    - ``latest (billing) ticket`` -> ``get_latest_incident`` with the
      category/status filters the question names.

    ``mcp_client`` always answers with a contract payload: transport/config
    failures surface as an honest ``unavailable`` result, which the routing
    then sends to ``tool_fallback``. Never invents state.
    """
    started = time.time()
    tool_payload: dict = {}
    sources = list(state.get("sources_used") or [])
    question = state["question"]
    ticket_id = extract_ticket_id(question)
    mode = "detail" if ticket_id is not None else "list"
    try:
        if ticket_id is None and mentions_rfp(question):
            mode = "latest_rfp"
            rfp_result = mcp_client.lookup_latest_rfp_via_mcp()
            tool_payload = rfp_result.model_dump()
            if "rfp" not in sources:
                sources = [*sources, "rfp"]
            answer = format_rfp_answer(rfp_result)
            return {
                "tool_result": tool_payload,
                "sources_used": sources,
                "answer": answer if rfp_result.ok else "",
            }
        latest = ticket_id is None and asks_for_latest_ticket(question)
        filters = extract_incident_filters(question) if latest else {}
        if latest:
            mode = "latest"
        payload = IncidentToolInput(ticket_id=ticket_id, latest=latest, **filters)
        result = mcp_client.lookup_incident_via_mcp(payload)
        tool_payload = result.model_dump()
        if "incidents" not in sources:
            sources = [*sources, "incidents"]
        answer = format_incident_answer(result)
        return {
            "tool_result": tool_payload,
            "sources_used": sources,
            "answer": answer if result.ok else "",
        }
    finally:
        _record_span(
            "lookup_incident",
            started,
            time.time(),
            {
                "source_kind": "rfp" if mode == "latest_rfp" else "incidents",
                "transport": "mcp",
                "mode": mode,
                "ok": bool(tool_payload.get("ok")),
                "error": tool_payload.get("error"),
                "n_incidents": len(tool_payload.get("incidents") or []),
                "ticket_id": ticket_id,
            },
        )


def lookup_inventory_node(state: AgentState) -> dict:
    """Call the inventory tool over MCP (the only transport); never invent stock."""
    started = time.time()
    tool_payload: dict = {}
    sources = list(state.get("sources_used") or [])
    try:
        sku = extract_sku(state["question"])
        name_query = None if sku else extract_inventory_name_query(state["question"])
        payload = InventoryToolInput(sku=sku, name_query=name_query)
        result = mcp_client.lookup_inventory_via_mcp(payload)
        tool_payload = result.model_dump()
        if "inventory" not in sources:
            sources = [*sources, "inventory"]
        answer = format_inventory_answer(result)
        return {
            "tool_result": tool_payload,
            "sources_used": sources,
            "answer": answer if result.ok else "",
        }
    finally:
        _record_span(
            "lookup_inventory",
            started,
            time.time(),
            {
                "source_kind": "inventory",
                "transport": "mcp",
                "ok": bool(tool_payload.get("ok")),
                "error": tool_payload.get("error"),
                "n_products": len(tool_payload.get("products") or []),
                "sku": extract_sku(state["question"]),
            },
        )


def _tool_facts_text(tool_result: dict, sources_used: list[str]) -> tuple[str, bool]:
    """Render the deterministic tool fact block; ``False`` when the tool failed."""
    from data.pipelines.agent_tools import (
        IncidentToolOutput,
        InventoryToolOutput,
    )

    if "rfp" in sources_used or "rfp_tickets" in (tool_result or {}):
        from data.pipelines.agent_tools import RFP_TOOL_FALLBACK, RfpToolOutput

        try:
            rfp = RfpToolOutput.model_validate(tool_result or {})
        except Exception:
            return RFP_TOOL_FALLBACK, False
        return format_rfp_answer(rfp), bool(rfp.ok)
    if "inventory" in sources_used or "products" in (tool_result or {}):
        try:
            result = InventoryToolOutput.model_validate(tool_result or {})
        except Exception:
            return INVENTORY_TOOL_FALLBACK, False
        return format_inventory_answer(result), bool(result.ok)
    from data.pipelines.agent_tools import IncidentToolOutput as _IncidentOut

    try:
        result = _IncidentOut.model_validate(tool_result or {})
    except Exception:
        return INCIDENT_TOOL_FALLBACK, False
    return format_incident_answer(result), bool(result.ok)


def tool_fallback_node(state: AgentState) -> dict:
    """Honest answer when an external tool failed or found nothing."""
    started = time.time()
    answer = ""
    try:
        tool_result = state.get("tool_result") or {}
        sources = state.get("sources_used") or []
        text, _ = _tool_facts_text(tool_result, list(sources))
        answer = text
        return {"answer": answer}
    finally:
        _record_span(
            "tool_fallback",
            started,
            time.time(),
            {
                "reason": (state.get("tool_result") or {}).get("error")
                or "tool_failed",
                "answer_chars": len(answer),
            },
        )


def answer_from_tool_node(state: AgentState) -> dict:
    """Surface a successful tool payload as the final answer (no LLM invent)."""
    started = time.time()
    answer = ""
    source_kind = "incidents"
    try:
        tool_result = state.get("tool_result") or {}
        sources = state.get("sources_used") or []
        text, _ = _tool_facts_text(tool_result, list(sources))
        answer = text
        if "inventory" in sources or "products" in tool_result:
            source_kind = "inventory"
        return {"answer": answer}
    finally:
        _record_span(
            "answer_from_tool",
            started,
            time.time(),
            {"answer_chars": len(answer), "source_kind": source_kind},
        )


def synthesize_hybrid_node(state: AgentState) -> dict:
    """Combine deterministic tool facts with the LLM policy paragraph.

    The live tool block is always rendered from the typed tool payload (never
    by the model), so ticket status / stock levels cannot be dropped or
    invented; the model only writes the policy part.
    """
    started = time.time()
    answer = ""
    tool_ok = False
    proposal: dict | None = None
    try:
        tool_result = state.get("tool_result") or {}
        sources = list(state.get("sources_used") or [])
        tool_text, tool_ok = _tool_facts_text(tool_result, sources)
        policy = list(state.get("context") or [])
        if tool_ok and policy:
            policy_text, proposal = rag_pipeline.generate_answer_with_proposal(
                state["question"],
                policy,
                memory=state.get("memory_context") or [],
            )
            answer = f"{tool_text}\n\n{policy_text}"
        elif tool_ok:
            answer = tool_text
        elif policy:
            policy_text, proposal = rag_pipeline.generate_answer_with_proposal(
                state["question"],
                policy,
                memory=state.get("memory_context") or [],
            )
            fallback = str(
                tool_result.get("message")
                or (
                    INVENTORY_TOOL_FALLBACK
                    if "inventory" in sources
                    else INCIDENT_TOOL_FALLBACK
                )
            )
            answer = f"{policy_text}\n\n{fallback}"
        else:
            answer = str(
                tool_result.get("message")
                or (
                    INVENTORY_TOOL_FALLBACK
                    if "inventory" in sources
                    else INCIDENT_TOOL_FALLBACK
                )
            )
        return {"answer": answer, "proposal": proposal or {}}
    finally:
        _record_span(
            "synthesize_hybrid",
            started,
            time.time(),
            {
                "answer_chars": len(answer),
                "tool_ok": tool_ok,
                "n_policy_chunks": len(state.get("context") or []),
                "has_proposal": bool(proposal),
            },
        )


# --- Memory orchestration (explicit interface in ``agent_memory``) ---


def _force_reject_pending(session_id: str) -> dict:
    """Discard any pending proposal without the decision LLM (jailbreak path).

    Injection text must never approve a pending memory. The outcome is
    audited as ``default_rejected`` with ``decision="jailbreak_precheck"``.
    """
    store = agent_memory.get_store()
    pending = store.get_pending(session_id)
    if pending is None:
        return {"action": "none"}
    store.append_audit(
        agent_memory.make_audit(
            agent_memory.ACTION_DEFAULT_REJECTED,
            session_id=session_id,
            proposal_id=pending.id,
            scope=pending.scope,
            category=pending.category,
            decision="jailbreak_precheck",
        )
    )
    store.clear_pending(session_id)
    return {"action": "default_rejected"}


def _resolve_pending_memory(session_id: str, question: str) -> dict:
    """Close the pending proposal, if any, before answering this message.

    The user's message is classified against the proposal with an explicit
    label. Silence, ambiguity or an unrelated message resolve as
    ``default_rejected`` — approval never happens by omission. Every outcome
    (approved, rejected, edited, PHI-blocked, default) lands in the audit
    trail; the pending slot is always cleared so only one proposal can be
    open per session.
    """
    store = agent_memory.get_store()
    pending = store.get_pending(session_id)
    if pending is None:
        return {"action": "none"}

    spanish = _is_spanish(question)
    bare = bare_memory_reply(question)
    if bare == "correct":
        # "correct me": keep the proposal open and ask for the right version;
        # the next message is classified as the edit.
        return {
            "action": "awaiting_correction",
            "proposal_id": pending.id,
            "standalone_answer": (
                MEMORY_ASK_CORRECTION_ES if spanish else MEMORY_ASK_CORRECTION_EN
            ),
        }
    if bare in ("approve", "reject"):
        decision = {"label": bare, "edited_fact": None}
    else:
        decision = memory_proposer.classify_decision(pending.model_dump(), question)
    label = decision.get("label") or "unrelated"
    edited_fact = decision.get("edited_fact")
    if label == "edit" and not edited_fact and bare is None and "?" not in question:
        # The user wants to correct the fact but has not said how yet.
        return {
            "action": "awaiting_correction",
            "proposal_id": pending.id,
            "standalone_answer": (
                MEMORY_ASK_CORRECTION_ES if spanish else MEMORY_ASK_CORRECTION_EN
            ),
        }
    base = {
        "session_id": session_id,
        "proposal_id": pending.id,
        "scope": pending.scope,
        "category": pending.category,
    }
    note = None
    action = "default_rejected"

    if label == "approve":
        verdict = memory_phi_guard.scan(pending.fact)
        if not verdict.allowed:
            action = "rejected_phi"
            store.append_audit(
                agent_memory.make_audit(
                    agent_memory.ACTION_REJECTED_PHI,
                    **base,
                    phi_reasons=verdict.reasons,
                )
            )
        else:
            entry = agent_memory.make_entry(
                scope=pending.scope,
                category=pending.category,
                fact=pending.fact,
                session_id=session_id,
                source_proposal_id=pending.id,
            )
            store.put_entry(entry)
            action = "approved"
            store.append_audit(
                agent_memory.make_audit(
                    agent_memory.ACTION_APPROVED,
                    **base,
                    fact=pending.fact,
                    decision="approve",
                )
            )
            note = _SAVENOTE_ES if _is_spanish(question) else _SAVENOTE_EN
    elif label == "edit":
        verdict = memory_phi_guard.scan(edited_fact or "")
        if not verdict.allowed or not edited_fact:
            action = "rejected_phi" if not verdict.allowed else "default_rejected"
            audit_kwargs = dict(base)
            if not verdict.allowed:
                audit_kwargs["phi_reasons"] = verdict.reasons
            store.append_audit(
                agent_memory.make_audit(
                    agent_memory.ACTION_REJECTED_PHI
                    if not verdict.allowed
                    else agent_memory.ACTION_DEFAULT_REJECTED,
                    **audit_kwargs,
                )
            )
        else:
            entry = agent_memory.make_entry(
                scope=pending.scope,
                category=pending.category,
                fact=edited_fact,
                session_id=session_id,
                source_proposal_id=pending.id,
            )
            store.put_entry(entry)
            action = "edited"
            store.append_audit(
                agent_memory.make_audit(
                    agent_memory.ACTION_EDITED,
                    **base,
                    decision="edit",
                    edited_fact=edited_fact,
                )
            )
            note = _SAVENOTE_ES if _is_spanish(question) else _SAVENOTE_EN
    elif label == "reject":
        action = "rejected"
        store.append_audit(
            agent_memory.make_audit(
                agent_memory.ACTION_REJECTED,
                **base,
                decision="reject",
            )
        )
        note = _REJECTNOTE_ES if _is_spanish(question) else _REJECTNOTE_EN
    else:  # unrelated / unknown label → discarded by default, audited
        action = "default_rejected"
        store.append_audit(
            agent_memory.make_audit(
                agent_memory.ACTION_DEFAULT_REJECTED,
                **base,
                decision=label,
            )
        )

    store.clear_pending(session_id)
    standalone: str | None = None
    # A bare decision ("Yes, save that for next time.") or a correction is
    # the whole message: answer with a clean confirmation instead of also
    # running it through the graph (which produced a generic greeting).
    if bare is not None or (action == "edited" and "?" not in question):
        standalone = {
            "approved": MEMORY_SAVED_ES if spanish else MEMORY_SAVED_EN,
            "edited": MEMORY_EDITED_ES if spanish else MEMORY_EDITED_EN,
            "rejected": MEMORY_REJECTED_ES if spanish else MEMORY_REJECTED_EN,
            "rejected_phi": (
                memory_phi_guard.PHI_REFUSAL_ES
                if spanish
                else memory_phi_guard.PHI_REFUSAL_EN
            ).strip(),
        }.get(action)
    return {
        "action": action,
        "note": None if standalone else note,
        "proposal_id": pending.id,
        "standalone_answer": standalone,
    }


def _propose_memory(
    session_id: str,
    question: str,
    answer: str,
    route: str | None,
    candidate: dict | None,
) -> dict:
    """Self-evaluate the finished answer: propose, or record "nothing to keep".

    ``candidate`` comes from the single structured call on LLM answer paths;
    tool-only paths self-evaluate with one structured call. The PHI screen
    runs **before** the proposal is shown to the user (HealthCore
    requirement); a blocked proposal produces an explicit refusal and an
    audit record with reason codes only (never the PHI text).
    """
    store = agent_memory.get_store()
    proposal = memory_proposer.normalize_proposal(candidate)
    if proposal is None and route in ("incidents", "inventory"):
        proposal = memory_proposer.propose_from_interaction(question, answer)
    elif proposal is None:
        # WebSocket chat streams via generate_answer (no structured proposal
        # field). Evaluate after the streamed answer so memory buttons still work.
        from data.pipelines.rag import _stream_hooks

        if _stream_hooks.get() is not None:
            proposal = memory_proposer.propose_from_interaction(question, answer)
    if not proposal:
        return {"action": "none"}

    base = {
        "session_id": session_id,
        "scope": proposal.get("scope", ""),
        "category": proposal.get("category", ""),
    }
    verdict = memory_phi_guard.scan_proposal(proposal)
    if not verdict.allowed:
        store.append_audit(
            agent_memory.make_audit(
                agent_memory.ACTION_REJECTED_PHI,
                **base,
                phi_reasons=verdict.reasons,
            )
        )
        return {
            "action": "rejected_phi",
            "phi_reasons": verdict.reasons,
            "suffix": memory_phi_guard.PHI_REFUSAL_ES
            if _is_spanish(question)
            else memory_phi_guard.PHI_REFUSAL_EN,
        }

    pending = agent_memory.make_pending(
        session_id=session_id,
        scope=proposal.get("scope", ""),
        category=proposal.get("category", ""),
        fact=proposal.get("fact", ""),
        reason=proposal.get("reason", ""),
        source_message=question,
    )
    if not store.set_pending(pending):
        # One open proposal per session: never stack a second one.
        store.append_audit(
            agent_memory.make_audit(
                agent_memory.ACTION_SKIPPED_PENDING, **base
            )
        )
        return {"action": "skipped_pending"}

    store.append_audit(
        agent_memory.make_audit(
            agent_memory.ACTION_PROPOSED,
            **base,
            proposal_id=pending.id,
            fact=pending.fact,
            status=agent_memory.STATUS_PENDING,
            expires_at=pending.expires_at,
        )
    )
    return {
        "action": "proposed",
        "proposal_id": pending.id,
        "suffix": PROPOSAL_QUESTION_ES
        if _is_spanish(question)
        else PROPOSAL_QUESTION_EN,
    }


def _memory_reply_result(
    question: str,
    session_id: str,
    trace: dict,
    started: float,
    resolution: dict,
    answer: str,
) -> dict:
    """Final state for a message that only answered the memory question."""
    finished = time.time()
    action = resolution.get("action", "none")
    trace.update(
        {
            "finished_at": finished,
            "duration_ms": round((finished - started) * 1000, 2),
            "status": "success",
            "route": "memory_reply",
            "scope": {"decision": "domain", "reasons": []},
            "memory": {
                "n_memory_facts": 0,
                "resolution": action,
                "proposal": "none",
            },
        }
    )
    logger.info(
        "agent_graph run %s answered the memory question (%s)",
        trace["trace_id"],
        action,
    )
    return {
        "question": question,
        "context": [],
        "answer": answer,
        "route": "memory_reply",
        "tool_result": {},
        "sources_used": [],
        "session_id": session_id,
        "memory_context": [],
        "proposal": {},
        "scope_decision": "domain",
        "scope_reasons": [],
        "trace_id": trace["trace_id"],
        # Still waiting for the corrected fact: keep the quick replies on.
        "memory_proposal_pending": action == "awaiting_correction",
    }


def _run_agent_once(
    question: str,
    session_id: str | None = None,
    *,
    memory_enabled: bool = True,
) -> dict:
    """Run the compiled graph for one question and return the final state + trace id.

    ``memory_enabled=False`` (used for the parts of a multi-question message)
    skips the pending-proposal resolution and the new-proposal step, so one
    numbered list never resolves or raises several memory proposals at once.

    ``session_id`` scopes the memory conversation (one pending proposal per
    session). Memory failures never break the answer: every memory step is
    wrapped and degrades to "nothing happened" with a warning log.

    Returns ``{"question": ..., "context": [...], "answer": ..., "route": ...,
    "tool_result": ..., "sources_used": [...], "session_id": ...,
    "memory_context": [...], "proposal": ..., "trace_id": ...,
    "memory_proposal_pending": bool}``.
    """
    session_id = (session_id or "").strip() or DEFAULT_MEMORY_SESSION
    trace_id = uuid.uuid4().hex
    started = time.time()
    # Deterministic pre-check (no LLM): a jailbreak must not resolve or
    # approve memory proposals, and must not receive injected facts.
    # Counted separately from the scope-check activation — this is the
    # memory-safety layer firing, not the scope layer.
    pre_jailbreak = bool(agent_scope_guard.detect_jailbreak(question))
    if pre_jailbreak:
        agent_content_guard.record_activation(
            "memory_precheck_reject", agent_content_guard.FAILURE_SECURITY
        )
        logger.warning(
            "guardrail memory_precheck_reject failure_type=%s session=%s",
            agent_content_guard.FAILURE_SECURITY,
            session_id,
        )
    trace: dict = {
        "trace_id": trace_id,
        "thread_id": trace_id,
        # Metadata only — never store raw staff/user text (PHI risk).
        "question_chars": len(question or ""),
        "session_id": session_id,
        "started_at": started,
        "finished_at": started,
        "duration_ms": 0.0,
        "status": "running",
        "n_chunks": 0,
        "sources": [],
        "sources_used": [],
        "route": None,
        "memory": {},
        "scope": {"decision": None, "reasons": []},
        "spans": [],
        "error": None,
    }
    _store_trace(trace)
    token = _current_trace_id.set(trace_id)
    try:
        # 1) Resolve any pending proposal BEFORE answering this message.
        # A jailbreak attempt is force-rejected without the decision LLM so
        # injection text can never approve a pending proposal.
        resolution: dict = {"action": "none"}
        try:
            agent_memory.maybe_sweep()
            if not memory_enabled:
                pass
            elif pre_jailbreak:
                resolution = _force_reject_pending(session_id)
            else:
                resolution = _resolve_pending_memory(session_id, question)
        except Exception:
            logger.exception("memory: pending resolution failed")
            resolution = {"action": "error"}

        standalone = resolution.get("standalone_answer")
        if standalone:
            return _memory_reply_result(
                question, session_id, trace, started, resolution, str(standalone)
            )

        # 2) Load approved facts relevant to this question (explicit store read).
        # Skipped for jailbreak attempts: injection text must not receive
        # memory-injected context.
        memory_context: list[dict] = []
        if not pre_jailbreak:
            try:
                store = agent_memory.get_store()
                entries = agent_memory.select_relevant(
                    store.list_entries(), question
                )
                memory_context = [
                    {
                        "scope": entry.scope,
                        "category": entry.category,
                        "fact": entry.fact,
                    }
                    for entry in entries
                ]
            except Exception:
                logger.exception("memory: context load failed")

        result = graph.invoke(
            {
                "question": question,
                "context": [],
                "answer": "",
                "route": "",
                "tool_result": {},
                "sources_used": [],
                "session_id": session_id,
                "memory_context": memory_context,
                "proposal": {},
                "scope_decision": "",
                "scope_reasons": [],
            },
            {"configurable": {"thread_id": trace_id}},
        )
        finished = time.time()
        context = result.get("context", [])
        sources_used = list(result.get("sources_used") or [])
        answer = result.get("answer") or ""
        scope_decision = str(result.get("scope_decision") or "domain")

        # 3) Self-evaluate the finished answer and act on the outcome.
        # Scope refusals never propose memory: there is nothing worth
        # remembering from a jailbreak or an off-domain personal request.
        proposal_summary: dict = {"action": "none"}
        if memory_enabled and scope_decision not in ("jailbreak", "personal_task"):
            try:
                proposal_summary = _propose_memory(
                    session_id,
                    question,
                    answer,
                    result.get("route"),
                    result.get("proposal") or None,
                )
            except Exception:
                logger.exception("memory: proposal step failed")
                proposal_summary = {"action": "error"}

        suffixes = [
            suffix
            for suffix in (
                resolution.get("note"),
                proposal_summary.get("suffix"),
            )
            if suffix
        ]
        if suffixes:
            answer = f"{answer}{''.join(suffixes)}"
            result["answer"] = answer

        # 4) Output guard: last gate before the answer reaches the user.
        # Catches empty answers, leaked internal prompt markers and
        # PHI-like content; fail-closed with a safe bilingual fallback
        # (never echoing the rejected text).
        output_verdict = agent_content_guard.validate_output(answer)
        if not output_verdict.allowed:
            answer = output_verdict.safe_answer
            result["answer"] = answer

        from data.pipelines.agent_guardrails import sanitize_agent_output

        safe_answer = sanitize_agent_output(str(answer or ""))
        if safe_answer != answer:
            answer = safe_answer
            result["answer"] = answer

        trace.update(
            {
                "finished_at": finished,
                "duration_ms": round((finished - started) * 1000, 2),
                "status": "success",
                "n_chunks": len(context),
                "sources": sorted(
                    {str(chunk.get("source_document", "")) for chunk in context}
                ),
                "sources_used": sources_used,
                "route": result.get("route") or None,
                "scope": {
                    "decision": scope_decision,
                    "reasons": list(result.get("scope_reasons") or []),
                },
                "output_guard": {
                    "allowed": output_verdict.allowed,
                    "reasons": list(output_verdict.reasons),
                    "failure_type": output_verdict.failure_type,
                },
                "memory": {
                    "n_memory_facts": len(memory_context),
                    "resolution": resolution.get("action", "none"),
                    "proposal": proposal_summary.get("action", "none"),
                },
            }
        )
        logger.info(
            "agent_graph run %s via %s sources=%s memory=%s in %.1fms",
            trace_id,
            [span["node"] for span in trace["spans"]],
            sources_used,
            f"{trace['memory']['resolution']}/{trace['memory']['proposal']}",
            trace["duration_ms"],
        )
        return {
            **result,
            "trace_id": trace_id,
            # UI hint: the agent just asked whether to remember something, so a
            # client can offer quick confirm/correct actions. Only the action
            # label is exposed, never the proposed fact (PHI/PII rule).
            "memory_proposal_pending": proposal_summary.get("action") == "proposed",
        }
    except Exception as exc:
        finished = time.time()
        trace.update(
            {
                "finished_at": finished,
                "duration_ms": round((finished - started) * 1000, 2),
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        # GenerationInterrupted is expected for chat abort — don't log as error.
        from data.pipelines.rag import GenerationInterrupted

        if isinstance(exc, GenerationInterrupted):
            raise
        logger.exception("agent_graph run %s failed", trace_id)
        raise
    finally:
        _current_trace_id.reset(token)



# --- Follow-up clarifications ("Which ticket?" -> "8") ---

_CLARIFICATION_TTL_SECONDS = 15 * 60
_MAX_CLARIFICATIONS = 1000
# session_id -> {"kind": "ticket" | "product", "at": epoch seconds}
_PENDING_CLARIFICATIONS: OrderedDict[str, dict] = OrderedDict()
_BARE_TICKET_REPLY_RE = re.compile(
    r"^\s*(?:(?:it'?s|the|ticket|incident|number|no\.?|n[uú]mero|caso|el)\s+)*"
    r"#?\s*(\d{1,7})\s*[.!]?\s*$",
    re.IGNORECASE,
)
_MAX_PRODUCT_REPLY_WORDS = 5


# Short acknowledgements are never a product name, even right after
# "Which product do you mean?" / "I could not find that product".
_ACK_REPLY_RE = re.compile(
    r"^\s*(?:ok(?:ay)?|thanks?(?: you)?|thank you|thx|cool|great|fine|sure|"
    r"yes|yeah|yep|no|nope|never ?mind|hi|hello|hey|bye|gracias|vale|"
    r"s[ií]|de acuerdo|hola|adi[oó]s|perfecto)\b",
    re.IGNORECASE,
)


def _clarification_kind(answer: str) -> str | None:
    """Which detail the agent just asked for (ticket id / product), if any.

    A "not found" answer counts too: the user usually replies with a
    corrected ticket number or product name ("syringes", "8"), which must be
    retried against the same tool instead of going to the knowledge base.
    """
    from data.pipelines.agent_tools import (
        INCIDENT_NOT_FOUND_MESSAGE,
        INCIDENT_TOOL_NEEDS_ID_MESSAGE,
        INVENTORY_NOT_FOUND_MESSAGE,
        INVENTORY_TOOL_NEEDS_PRODUCT_MESSAGE,
    )

    text = (answer or "").strip()
    if text.startswith((INCIDENT_TOOL_NEEDS_ID_MESSAGE, INCIDENT_NOT_FOUND_MESSAGE)):
        return "ticket"
    if text.startswith(
        (INVENTORY_TOOL_NEEDS_PRODUCT_MESSAGE, INVENTORY_NOT_FOUND_MESSAGE)
    ):
        return "product"
    return None


def _remember_clarification(session_id: str, answer: str) -> None:
    """Store (or clear) the one-shot follow-up expectation for a session."""
    kind = _clarification_kind(answer)
    _PENDING_CLARIFICATIONS.pop(session_id, None)
    if kind is None:
        return
    _PENDING_CLARIFICATIONS[session_id] = {"kind": kind, "at": time.time()}
    while len(_PENDING_CLARIFICATIONS) > _MAX_CLARIFICATIONS:
        _PENDING_CLARIFICATIONS.popitem(last=False)


def resolve_follow_up(session_id: str, message: str) -> str:
    """Rewrite a bare follow-up ("8") into a full question using the last turn.

    Only applies right after the agent asked "Which ticket/product do you
    mean?" (or answered "I could not find that ticket/product") in the same
    session, within a short TTL, and only when the reply
    is clearly the missing detail (a bare number / a short product name that
    does not route anywhere else on its own). Otherwise the message is
    returned unchanged. The expectation is one-shot: it is consumed here.
    """
    pending = _PENDING_CLARIFICATIONS.pop(session_id, None)
    text = (message or "").strip()
    if not pending or not text:
        return message
    if bare_memory_reply(text) is not None:
        # "Save it" / "no" answer a memory question, not "which product?".
        return message
    if time.time() - float(pending.get("at", 0)) > _CLARIFICATION_TTL_SECONDS:
        return message
    if pending.get("kind") == "ticket":
        match = _BARE_TICKET_REPLY_RE.match(text)
        if match:
            return f"What is the status of ticket {int(match.group(1))}?"
        return message
    if pending.get("kind") == "product":
        words = re.sub(r"[¿?¡!.,;:]", " ", text).split()
        if (
            0 < len(words) <= _MAX_PRODUCT_REPLY_WORDS
            and classify_route(text) == "rag"
            and not has_policy_signal(text)
            and not _ACK_REPLY_RE.match(text)
        ):
            return f"What is the current stock of {' '.join(words)}?"
    return message


# --- Several numbered questions in one message ---

_NUMBERED_ITEM_RE = re.compile(r"(?:^|(?<=\s))(\d{1,2})[.)]\s+")
_MAX_SUB_QUESTIONS = 6
MULTI_PART_FAILURE_MESSAGE = (
    "I could not answer this part right now. Please ask it again on its own."
)


def split_numbered_questions(text: str) -> list[str]:
    """``"1. A 2. B"`` / one item per line -> ``["A", "B"]``; else ``[]``.

    Items must be numbered 1, 2, 3 … in order; at least two are needed.
    Text after the last marker belongs to the last item.
    """
    markers: list[re.Match[str]] = []
    expected = 1
    for match in _NUMBERED_ITEM_RE.finditer(text or ""):
        if int(match.group(1)) == expected:
            markers.append(match)
            expected += 1
    if len(markers) < 2:
        return []
    parts: list[str] = []
    for index, match in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        part = " ".join(text[match.end() : end].split())
        if part:
            parts.append(part)
    if len(parts) < 2:
        return []
    return parts[:_MAX_SUB_QUESTIONS]


def _is_guarded_message(question: str) -> bool:
    """Jailbreak / PHI-exfil messages keep the single-run refusal path."""
    from data.pipelines.agent_guardrails import is_phi_exfil_attempt

    return bool(agent_scope_guard.detect_jailbreak(question)) or bool(
        is_phi_exfil_attempt(question)
    )


def _run_multi(question: str, parts: list[str], session_id: str) -> dict:
    """Answer each numbered question separately; one failure never hides the rest."""
    from data.pipelines.rag import GenerationInterrupted

    started = time.time()
    answers: list[str] = []
    sources_used: list[str] = []
    part_traces: list[dict] = []
    for index, part in enumerate(parts, start=1):
        try:
            result = _run_agent_once(part, session_id, memory_enabled=False)
            answer = str(result.get("answer") or "").strip()
            part_traces.append(
                {"trace_id": result.get("trace_id"), "route": result.get("route")}
            )
            for source in result.get("sources_used") or []:
                if source not in sources_used:
                    sources_used.append(source)
        except GenerationInterrupted:
            raise
        except Exception:
            logger.exception("agent_graph multi-question part %s failed", index)
            answer = MULTI_PART_FAILURE_MESSAGE
            part_traces.append({"trace_id": None, "route": "error"})
        answers.append(f"**{index}.** {answer or MULTI_PART_FAILURE_MESSAGE}")
    combined = "\n\n".join(answers)
    finished = time.time()
    trace_id = uuid.uuid4().hex
    _store_trace(
        {
            "trace_id": trace_id,
            "thread_id": trace_id,
            "question_chars": len(question or ""),
            "session_id": session_id,
            "started_at": started,
            "finished_at": finished,
            "duration_ms": round((finished - started) * 1000, 2),
            "status": "success",
            "route": "multi",
            "sources_used": sources_used,
            "parts": part_traces,
            "spans": [],
            "error": None,
        }
    )
    return {
        "question": question,
        "context": [],
        "answer": combined,
        "route": "multi",
        "tool_result": {},
        "sources_used": sources_used,
        "session_id": session_id,
        "memory_context": [],
        "proposal": {},
        "trace_id": trace_id,
        "parts": part_traces,
        "memory_proposal_pending": False,
    }


def run_agent(question: str, session_id: str | None = None) -> dict:
    """Public entry point: follow-ups, numbered lists, then the graph.

    - A bare reply to "Which ticket/product do you mean?" is rewritten with
      the previous turn (``resolve_follow_up``).
    - A message with several numbered questions is answered part by part
      (``split_numbered_questions``), unless it trips the jailbreak / PHI
      screens — those keep the single-run refusal path unchanged.
    - Everything else runs the graph once (``_run_agent_once``).
    """
    session = (session_id or "").strip() or DEFAULT_MEMORY_SESSION
    if _is_guarded_message(question):
        _PENDING_CLARIFICATIONS.pop(session, None)
        return _run_agent_once(question, session)
    parts = split_numbered_questions(question)
    if parts:
        _PENDING_CLARIFICATIONS.pop(session, None)
        return _run_multi(question, parts, session)
    effective = resolve_follow_up(session, question)
    result = _run_agent_once(effective, session)
    _remember_clarification(session, str(result.get("answer") or ""))
    return result


def run_agent_stream(
    question: str,
    *,
    thread_id: str,
    on_token: Callable[[str], None],
    cancel_check: Callable[[], bool],
) -> dict:
    """Same graph as :func:`run_agent`, streaming LLM tokens via ``on_token``.

    Memory is scoped to ``thread_id`` (the chat session). When the structured
    generation path is used, tokens may arrive as a single trailing chunk.
    Raises :class:`data.pipelines.rag.GenerationInterrupted` when cancelled.
    """
    from data.pipelines.rag import (
        GenerationInterrupted,
        reset_stream_hooks,
        set_stream_hooks,
    )

    parts: list[str] = []

    def _on_token(tok: str) -> None:
        if cancel_check():
            raise GenerationInterrupted("chat generation cancelled")
        parts.append(tok)
        on_token(tok)

    def _cancel_only(_tok: str) -> None:
        if cancel_check():
            raise GenerationInterrupted("chat generation cancelled")

    # Numbered multi-question messages are answered part by part; streaming
    # each part's tokens would interleave them, so the combined answer is
    # emitted once at the end instead (cancellation still applies).
    is_multi = bool(split_numbered_questions(question)) and not _is_guarded_message(
        question
    )
    hooks_token = set_stream_hooks(_cancel_only if is_multi else _on_token, cancel_check)
    try:
        result = run_agent(question, session_id=thread_id)
        answer = (result.get("answer") or "").strip()
        emitted_text = "".join(parts)
        if answer.startswith(emitted_text) and len(answer) > len(emitted_text):
            remainder = answer[len(emitted_text):]
            if remainder:
                if cancel_check():
                    raise GenerationInterrupted("chat generation cancelled")
                on_token(remainder)
        elif not parts and answer:
            if cancel_check():
                raise GenerationInterrupted("chat generation cancelled")
            on_token(answer)
        result["stream_status"] = "completed"
        return result
    except GenerationInterrupted:
        raise
    finally:
        reset_stream_hooks(hooks_token)


# --- Conditional edges: explicit routing, never a hardcoded straight line ---


def route_question(
    state: AgentState,
) -> Literal["refuse", "refuse_security", "scope_check"]:
    """Blank → refuse; PHI-exfil → refuse_security; else screen scope."""
    from data.pipelines.agent_guardrails import is_phi_exfil_attempt

    question = state["question"].strip()
    if not question:
        return "refuse"
    if is_phi_exfil_attempt(question):
        return "refuse_security"
    return "scope_check"


def route_after_scope(
    state: AgentState,
) -> Literal["scope_refusal", "casual_redirect", "decide_route"]:
    """Refuse jailbreak/personal tasks; redirect casual; domain → tools/RAG."""
    decision = state.get("scope_decision") or "domain"
    if decision in ("jailbreak", "personal_task"):
        return "scope_refusal"
    if decision == "casual":
        return "casual_redirect"
    return "decide_route"


def route_after_decide(
    state: AgentState,
) -> Literal["lookup_incident", "lookup_inventory", "retrieve"]:
    """Send operational/hybrid questions to their API tool; policies to RAG."""
    route = state.get("route")
    if route in ("incidents", "hybrid_incidents"):
        return "lookup_incident"
    if route in ("inventory", "hybrid_inventory"):
        return "lookup_inventory"
    return "retrieve"


def route_context(
    state: AgentState,
) -> Literal["honest", "generate", "synthesize_hybrid"]:
    """Hybrid synthesizes tool facts + policy; else honest/generate as Part 1."""
    if is_hybrid_route(state.get("route")):
        return "synthesize_hybrid"
    return "honest" if not state["context"] else "generate"


def route_after_tool(
    state: AgentState,
) -> Literal["answer_from_tool", "tool_fallback", "retrieve"]:
    """Tool-only ends here; hybrid continues to RAG so the trace shows both."""
    if is_hybrid_route(state.get("route")):
        return "retrieve"
    tool_result = state.get("tool_result") or {}
    if tool_result.get("ok"):
        return "answer_from_tool"
    return "tool_fallback"


_checkpointer = MemorySaver()

_builder = StateGraph(AgentState)
_builder.add_node("receive", receive_node)
_builder.add_node("scope_check", scope_check_node)
_builder.add_node("scope_refusal", scope_refusal_node)
_builder.add_node("casual_redirect", casual_redirect_node)
_builder.add_node("decide_route", decide_route_node)
_builder.add_node("retrieve", retrieve_node)
_builder.add_node("generate", generate_node)
_builder.add_node("refuse", refuse_node)
_builder.add_node("refuse_security", refuse_security_node)
_builder.add_node("honest", honest_node)
_builder.add_node("lookup_incident", lookup_incident_node)
_builder.add_node("lookup_inventory", lookup_inventory_node)
_builder.add_node("tool_fallback", tool_fallback_node)
_builder.add_node("answer_from_tool", answer_from_tool_node)
_builder.add_node("synthesize_hybrid", synthesize_hybrid_node)
_builder.add_edge(START, "receive")
_builder.add_conditional_edges("receive", route_question)
_builder.add_conditional_edges("scope_check", route_after_scope)
_builder.add_conditional_edges("decide_route", route_after_decide)
_builder.add_conditional_edges("retrieve", route_context)
_builder.add_conditional_edges("lookup_incident", route_after_tool)
_builder.add_conditional_edges("lookup_inventory", route_after_tool)
_builder.add_edge("refuse", END)
_builder.add_edge("refuse_security", END)
_builder.add_edge("scope_refusal", END)
_builder.add_edge("casual_redirect", END)
_builder.add_edge("honest", END)
_builder.add_edge("generate", END)
_builder.add_edge("tool_fallback", END)
_builder.add_edge("answer_from_tool", END)
_builder.add_edge("synthesize_hybrid", END)

# Compiled at import time: structural errors surface on import, not in production.
graph = _builder.compile(checkpointer=_checkpointer)




if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: uv run python -m data.pipelines.agent_graph "your question"'
        )
    outcome = run_agent(sys.argv[1])
    print(outcome["answer"])
    print(f"[trace_id={outcome['trace_id']} sources={outcome.get('sources_used')}]")
