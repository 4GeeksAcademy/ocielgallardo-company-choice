"""Explicit read/write interface for the agent's persistent (episodic) memory.

Responsibility: store, pending-proposal lifecycle, audit trail and
consolidation for facts the user approved the agent to remember. This is a
**separate store** from the company RAG knowledge base: the namespace is
always ``agent:memory:*`` and nothing here ever writes to the Qdrant
``*_knowledge`` collection (RAG stays read-only tooling).

Design summary (decision record lives in the PR / memory-bank):

- Backend: key/value. ``InMemoryMemoryStore`` for tests and local runs;
  ``RedisMemoryStore`` when ``AGENT_MEMORY_BACKEND=redis`` (Compose already
  ships Redis). Episodic facts are retrieved by scope/category + token
  relevance, so semantic vector search is unnecessary for the volume the
  briefing describes, and a knowledge graph buys nothing until explicit
  relation traversal becomes a real requirement.
- One pending proposal per session (``set_pending`` refuses a second one);
  silence expires it (``pending_ttl_hours``) and the sweep records the
  default rejection in the audit trail.
- Every proposal outcome is auditable, approved or not. Source messages
  that contain possible PHI are redacted before being stored (codes only).
- Consolidation runs after every write: expired entries drop, duplicates
  merge (normalized / near-duplicate facts), the per-key cap keeps the
  newest entries, and every kept fact is re-screened for PHI before it is
  written back.

Run:
    uv run python -m data.pipelines.agent_memory consolidate
    uv run python -m data.pipelines.agent_memory audit
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Protocol

from pydantic import BaseModel, Field

from data.pipelines import memory_phi_guard

logger = logging.getLogger(__name__)

# --- Domain vocabulary (kept here so store + proposer share one contract) ---

CATEGORIES = (
    "hours",
    "procedure",
    "supplier",
    "incident_pattern",
    "staff_preference",
    "other",
)

ACTION_PROPOSED = "proposed"
ACTION_APPROVED = "approved"
ACTION_REJECTED = "rejected"
ACTION_EDITED = "edited"
ACTION_REJECTED_PHI = "rejected_phi"
ACTION_DEFAULT_REJECTED = "default_rejected"
ACTION_EXPIRED_DEFAULT_REJECTED = "expired_default_rejected"
ACTION_SKIPPED_PENDING = "skipped_pending"
ACTION_CONSOLIDATED = "consolidated"

STATUS_PENDING = "pending"
STATUS_FINAL = "final"

NAMESPACE = "agent:memory"
FORBIDDEN_NAMESPACE_FRAGMENT = "knowledge"

REDACTED_MESSAGE = "[redacted: message may contain PHI]"
MAX_MESSAGE_CHARS = 500
MAX_FACT_CHARS = 500


# --- Settings ---


@dataclass(frozen=True)
class MemorySettings:
    """Environment-driven memory configuration (root ``.env``)."""

    backend: str
    redis_url: str
    entry_ttl_days: int
    max_entries_per_key: int
    audit_max: int
    audit_ttl_days: int
    pending_ttl_hours: int
    sweep_interval_s: int

    @classmethod
    def from_env(cls) -> MemorySettings:
        return cls(
            backend=os.getenv("AGENT_MEMORY_BACKEND", "memory").strip().lower(),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            entry_ttl_days=_env_int("AGENT_MEMORY_TTL_DAYS", 180),
            max_entries_per_key=_env_int("AGENT_MEMORY_MAX_ENTRIES_PER_KEY", 20),
            audit_max=_env_int("AGENT_MEMORY_AUDIT_MAX", 1000),
            audit_ttl_days=_env_int("AGENT_MEMORY_AUDIT_TTL_DAYS", 90),
            pending_ttl_hours=_env_int("AGENT_MEMORY_PENDING_TTL_HOURS", 168),
            sweep_interval_s=_env_int("AGENT_MEMORY_SWEEP_INTERVAL_S", 600),
        )


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


# --- Models ---


class MemoryEntry(BaseModel):
    """An approved, durable fact the agent remembers."""

    id: str
    scope: str
    category: str
    fact: str
    source_proposal_id: str = ""
    session_id: str = ""
    created_at: str
    updated_at: str
    expires_at: str


class PendingProposal(BaseModel):
    """A proposal waiting for the user's explicit decision (at most one/session)."""

    id: str
    session_id: str
    scope: str
    category: str
    fact: str
    reason: str = ""
    source_message: str = ""
    created_at: str
    expires_at: str


class AuditRecord(BaseModel):
    """Append-only record of a proposal outcome (approved or not)."""

    id: str
    action: str
    created_at: str
    session_id: str = ""
    proposal_id: str = ""
    scope: str = ""
    category: str = ""
    fact: str | None = None
    decision: str | None = None
    edited_fact: str | None = None
    phi_reasons: list[str] = Field(default_factory=list)
    message_redacted: bool = False
    status: str = STATUS_FINAL
    expires_at: str | None = None


class StoreError(RuntimeError):
    """Memory backend unavailable — callers degrade, never fail the answer."""


# --- Time / text helpers ---


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_scope(text: str | None) -> str:
    """Clinic/scope label: lowercase, collapsed, bounded; empty → network."""
    cleaned = re.sub(r"[^\w\s-]", " ", str(text or "")).strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:60] or "network"


def normalize_category(text: str | None) -> str:
    cleaned = str(text or "").strip().lower()
    return cleaned if cleaned in CATEGORIES else "other"


def new_id() -> str:
    return uuid.uuid4().hex


def redact_message(text: str | None) -> tuple[str, bool]:
    """Return a storable message and whether it was redacted (possible PHI)."""
    verdict = memory_phi_guard.scan(text)
    if not verdict.allowed:
        return REDACTED_MESSAGE, True
    return (text or "")[:MAX_MESSAGE_CHARS], False


def clamp_fact(text: str | None) -> str:
    return (str(text or "")).strip()[:MAX_FACT_CHARS]


# --- Pure helpers: relevance + consolidation ---

_STOPWORDS = frozenset(
    """a an and are as at be by do does for from has have how i in is it of on
    or that the this to was we what when where which who why will with
    el la los las un una unos unas y o de del que en es son por para con su
    sus lo le les cómo cual cuales cuando donde quien porque há cuándo hay""".split()
)

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall((text or "").lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def select_relevant(
    entries: Iterable[MemoryEntry], question: str, *, limit: int = 5
) -> list[MemoryEntry]:
    """Pick the entries most relevant to ``question`` by token overlap.

    Pure and cheap: scope/category/fact tokens vs question tokens. Entries
    with zero overlap are not injected — unrelated memories must not leak
    into an answer.
    """
    question_tokens = tokenize(question)
    if not question_tokens:
        return []
    scored: list[tuple[int, MemoryEntry]] = []
    for entry in entries:
        fact_tokens = tokenize(f"{entry.scope} {entry.category} {entry.fact}")
        overlap = question_tokens & fact_tokens
        if not overlap:
            continue
        score = len(overlap)
        if tokenize(entry.scope) & question_tokens:
            score += 2
        scored.append((score, entry))
    scored.sort(key=lambda pair: (pair[0], pair[1].updated_at), reverse=True)
    return [entry for _, entry in scored[:limit]]


def _normalized_fact(fact: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", (fact or "").lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def consolidate_entries(
    entries: Iterable[MemoryEntry],
    *,
    now: datetime | None = None,
    ttl_days: int = 180,
    max_per_key: int = 20,
    scan=memory_phi_guard.scan,
) -> tuple[list[MemoryEntry], list[dict]]:
    """Apply the documented cleanup policy to one (scope, category) bucket.

    Policy: drop expired entries, merge duplicates (normalized equality or
    Jaccard >= 0.9 over fact tokens — the newest version wins), keep only the
    ``max_per_key`` newest survivors, and re-screen every kept fact for PHI
    (briefing: consolidation must re-verify, not trust the first check).
    Returns ``(kept, dropped)`` where each drop carries a machine reason.
    """
    now = now or utc_now()
    dropped: list[dict] = []
    alive: list[MemoryEntry] = []
    for entry in entries:
        expires = parse_iso(entry.expires_at)
        if expires is not None and expires <= now:
            dropped.append({"id": entry.id, "reason": "expired"})
            continue
        alive.append(entry)

    alive.sort(key=lambda entry: entry.updated_at, reverse=True)
    kept: list[MemoryEntry] = []
    kept_tokens: list[set[str]] = []
    for entry in alive:
        fact_tokens = tokenize(entry.fact)
        merged = False
        for index, previous_tokens in enumerate(kept_tokens):
            same_norm = _normalized_fact(entry.fact) == _normalized_fact(
                kept[index].fact
            )
            if same_norm or _jaccard(fact_tokens, previous_tokens) >= 0.9:
                dropped.append({"id": entry.id, "reason": "duplicate"})
                merged = True
                break
        if merged:
            continue
        kept.append(entry)
        kept_tokens.append(fact_tokens)

    if len(kept) > max_per_key:
        for entry in kept[max_per_key:]:
            dropped.append({"id": entry.id, "reason": "cap"})
        kept = kept[:max_per_key]

    survivors: list[MemoryEntry] = []
    for entry in kept:
        verdict = scan(entry.fact)
        if not verdict.allowed:
            dropped.append({"id": entry.id, "reason": "phi"})
            logger.warning(
                "consolidation dropped entry %s: PHI screen (%s)",
                entry.id,
                ",".join(verdict.reasons),
            )
            continue
        survivors.append(entry)
    return survivors, dropped


def make_entry(
    *,
    scope: str,
    category: str,
    fact: str,
    session_id: str = "",
    source_proposal_id: str = "",
    now: datetime | None = None,
    ttl_days: int = 180,
) -> MemoryEntry:
    now = now or utc_now()
    created = iso(now)
    return MemoryEntry(
        id=new_id(),
        scope=normalize_scope(scope),
        category=normalize_category(category),
        fact=clamp_fact(fact),
        source_proposal_id=source_proposal_id,
        session_id=session_id,
        created_at=created,
        updated_at=created,
        expires_at=iso(now + timedelta(days=ttl_days)),
    )


def make_pending(
    *,
    session_id: str,
    scope: str,
    category: str,
    fact: str,
    reason: str = "",
    source_message: str = "",
    now: datetime | None = None,
    pending_ttl_hours: int = 168,
) -> PendingProposal:
    now = now or utc_now()
    safe_message, _redacted = redact_message(source_message)
    return PendingProposal(
        id=new_id(),
        session_id=session_id,
        scope=normalize_scope(scope),
        category=normalize_category(category),
        fact=clamp_fact(fact),
        reason=clamp_fact(reason),
        source_message=safe_message,
        created_at=iso(now),
        expires_at=iso(now + timedelta(hours=pending_ttl_hours)),
    )


def make_audit(
    action: str,
    *,
    session_id: str = "",
    proposal_id: str = "",
    scope: str = "",
    category: str = "",
    fact: str | None = None,
    decision: str | None = None,
    edited_fact: str | None = None,
    phi_reasons: list[str] | None = None,
    message_redacted: bool = False,
    status: str = STATUS_FINAL,
    expires_at: str | None = None,
    now: datetime | None = None,
) -> AuditRecord:
    return AuditRecord(
        id=new_id(),
        action=action,
        created_at=iso(now or utc_now()),
        session_id=session_id,
        proposal_id=proposal_id,
        scope=normalize_scope(scope) if scope else "",
        category=normalize_category(category) if category else "",
        fact=fact,
        decision=decision,
        edited_fact=edited_fact,
        phi_reasons=list(phi_reasons or []),
        message_redacted=message_redacted,
        status=status,
        expires_at=expires_at,
    )


# --- Store contract ---


class MemoryStore(Protocol):
    """Explicit read/write interface — the agent never scribbles state ad hoc."""

    def get_pending(self, session_id: str) -> PendingProposal | None: ...

    def set_pending(self, proposal: PendingProposal) -> bool: ...

    def clear_pending(self, session_id: str) -> None: ...

    def list_entries(self) -> list[MemoryEntry]: ...

    def put_entry(self, entry: MemoryEntry) -> list[dict]: ...

    def append_audit(self, record: AuditRecord) -> None: ...

    def list_audit(self) -> list[AuditRecord]: ...

    def replace_audit(self, records: list[AuditRecord]) -> None: ...


def _entry_key(scope: str, category: str) -> str:
    return f"{NAMESPACE}:entries:{normalize_scope(scope)}:{normalize_category(category)}"


def _assert_agent_namespace(key: str) -> None:
    """Hard guard: agent memory never touches the company knowledge store."""
    if not key.startswith(NAMESPACE):
        raise StoreError(f"refusing non-agent-memory key: {key}")
    if FORBIDDEN_NAMESPACE_FRAGMENT in key:
        raise StoreError(f"refusing knowledge-like key: {key}")


# --- In-memory backend (tests, local runs, fallback) ---


class InMemoryMemoryStore:
    """Process-local store. Same contract as Redis; lost on restart."""

    def __init__(self, settings: MemorySettings | None = None) -> None:
        self.settings = settings or MemorySettings.from_env()
        self._pending: dict[str, PendingProposal] = {}
        self._entries: dict[str, list[MemoryEntry]] = {}
        self._audit: list[AuditRecord] = []

    def get_pending(self, session_id: str) -> PendingProposal | None:
        proposal = self._pending.get(session_id)
        if proposal is None:
            return None
        expires = parse_iso(proposal.expires_at)
        if expires is not None and expires <= utc_now():
            self._pending.pop(session_id, None)
            return None
        return proposal.model_copy(deep=True)

    def set_pending(self, proposal: PendingProposal) -> bool:
        if proposal.session_id in self._pending:
            return False
        self._pending[proposal.session_id] = proposal.model_copy(deep=True)
        return True

    def clear_pending(self, session_id: str) -> None:
        self._pending.pop(session_id, None)

    def list_entries(self) -> list[MemoryEntry]:
        now = utc_now()
        alive: list[MemoryEntry] = []
        for bucket in self._entries.values():
            for entry in bucket:
                expires = parse_iso(entry.expires_at)
                if expires is not None and expires <= now:
                    continue
                alive.append(entry.model_copy(deep=True))
        return alive

    def put_entry(self, entry: MemoryEntry) -> list[dict]:
        key = _entry_key(entry.scope, entry.category)
        _assert_agent_namespace(key)
        bucket = self._entries.setdefault(key, [])
        bucket[:] = [item for item in bucket if item.id != entry.id]
        bucket.append(entry.model_copy(deep=True))
        kept, dropped = consolidate_entries(
            bucket,
            ttl_days=self.settings.entry_ttl_days,
            max_per_key=self.settings.max_entries_per_key,
        )
        self._entries[key] = kept
        if dropped:
            self.append_audit(
                make_audit(
                    ACTION_CONSOLIDATED,
                    scope=entry.scope,
                    category=entry.category,
                    fact=None,
                    now=utc_now(),
                )
            )
        return dropped

    def append_audit(self, record: AuditRecord) -> None:
        self._audit.append(record.model_copy(deep=True))
        if len(self._audit) > self.settings.audit_max:
            self._audit = self._audit[-self.settings.audit_max :]

    def list_audit(self) -> list[AuditRecord]:
        return [record.model_copy(deep=True) for record in self._audit]

    def replace_audit(self, records: list[AuditRecord]) -> None:
        self._audit = [record.model_copy(deep=True) for record in records]


# --- Redis backend (Compose / production) ---


class RedisMemoryStore:
    """Redis-backed store. ``decode_responses=True``; JSON payloads."""

    def __init__(
        self, settings: MemorySettings | None = None, client=None
    ) -> None:
        self.settings = settings or MemorySettings.from_env()
        if client is not None:
            self._client = client
            return
        try:
            import redis as redis_lib
        except ImportError as exc:  # pragma: no cover - dependency is declared
            raise StoreError("redis package is not installed") from exc
        try:
            self._client = redis_lib.Redis.from_url(
                self.settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            self._client.ping()
        except Exception as exc:
            raise StoreError(f"redis unreachable: {exc}") from exc

    # Keys
    def _pending_key(self, session_id: str) -> str:
        key = f"{NAMESPACE}:pending:{session_id}"
        _assert_agent_namespace(key)
        return key

    def _audit_key(self) -> str:
        key = f"{NAMESPACE}:audit"
        _assert_agent_namespace(key)
        return key

    def _index_key(self) -> str:
        key = f"{NAMESPACE}:index"
        _assert_agent_namespace(key)
        return key

    def get_pending(self, session_id: str) -> PendingProposal | None:
        raw = self._client.get(self._pending_key(session_id))
        if not raw:
            return None
        proposal = PendingProposal.model_validate(json.loads(raw))
        expires = parse_iso(proposal.expires_at)
        if expires is not None and expires <= utc_now():
            self._client.delete(self._pending_key(session_id))
            return None
        return proposal

    def set_pending(self, proposal: PendingProposal) -> bool:
        key = self._pending_key(proposal.session_id)
        if self._client.get(key):
            return False
        expires = parse_iso(proposal.expires_at)
        ttl_seconds = self.settings.pending_ttl_hours * 3600
        if expires is not None:
            ttl_seconds = max(1, int((expires - utc_now()).total_seconds()))
        self._client.set(key, proposal.model_dump_json(), ex=ttl_seconds)
        return True

    def clear_pending(self, session_id: str) -> None:
        self._client.delete(self._pending_key(session_id))

    def list_entries(self) -> list[MemoryEntry]:
        now = utc_now()
        alive: list[MemoryEntry] = []
        for key in self._client.smembers(self._index_key()):
            for raw in self._client.lrange(key, 0, -1):
                entry = MemoryEntry.model_validate(json.loads(raw))
                expires = parse_iso(entry.expires_at)
                if expires is not None and expires <= now:
                    continue
                alive.append(entry)
        return alive

    def put_entry(self, entry: MemoryEntry) -> list[dict]:
        key = _entry_key(entry.scope, entry.category)
        _assert_agent_namespace(key)
        bucket: list[MemoryEntry] = []
        for raw in self._client.lrange(key, 0, -1):
            existing = MemoryEntry.model_validate(json.loads(raw))
            if existing.id != entry.id:
                bucket.append(existing)
        bucket.append(entry)
        kept, dropped = consolidate_entries(
            bucket,
            ttl_days=self.settings.entry_ttl_days,
            max_per_key=self.settings.max_entries_per_key,
        )
        self._client.delete(key)
        for survivor in kept:
            self._client.rpush(key, survivor.model_dump_json())
        if kept:
            self._client.expire(
                key, self.settings.entry_ttl_days * 86400
            )
            self._client.sadd(self._index_key(), key)
            self._client.expire(self._index_key(), self.settings.entry_ttl_days * 86400)
        if dropped:
            self.append_audit(
                make_audit(
                    ACTION_CONSOLIDATED,
                    scope=entry.scope,
                    category=entry.category,
                    fact=None,
                )
            )
        return dropped

    def append_audit(self, record: AuditRecord) -> None:
        key = self._audit_key()
        self._client.rpush(key, record.model_dump_json())
        self._client.ltrim(key, -self.settings.audit_max, -1)
        self._client.expire(key, self.settings.audit_ttl_days * 86400)

    def list_audit(self) -> list[AuditRecord]:
        raw_records = self._client.lrange(self._audit_key(), 0, -1)
        return [
            AuditRecord.model_validate(json.loads(raw)) for raw in raw_records
        ]

    def replace_audit(self, records: list[AuditRecord]) -> None:
        key = self._audit_key()
        self._client.delete(key)
        for record in records:
            self._client.rpush(key, record.model_dump_json())
        if records:
            self._client.ltrim(key, -self.settings.audit_max, -1)
            self._client.expire(key, self.settings.audit_ttl_days * 86400)


# --- Lifecycle / sweep ---


_store: MemoryStore | None = None
_last_sweep = 0.0


def get_store() -> MemoryStore:
    """Lazily build the configured store (Redis when enabled, else memory)."""
    global _store
    if _store is not None:
        return _store
    settings = MemorySettings.from_env()
    if settings.backend == "redis":
        try:
            _store = RedisMemoryStore(settings)
            return _store
        except StoreError as exc:
            logger.warning(
                "agent memory: redis unavailable (%s); falling back to in-memory",
                exc,
            )
    _store = InMemoryMemoryStore(settings)
    return _store


def set_store(store: MemoryStore | None) -> None:
    """Test/demo hook: install a store instance (None → next get_store rebuilds)."""
    global _store
    _store = store


def reset_store() -> None:
    set_store(None)


def maybe_sweep(store: MemoryStore | None = None, *, force: bool = False) -> int:
    """Record silence as rejection: expire stale *pending* audit records.

    A pending proposal the user never answered is discarded by the store TTL;
    this sweep makes that visible in the audit trail
    (``expired_default_rejected``). Throttled to once per
    ``sweep_interval_s`` per process.
    """
    global _last_sweep
    settings = MemorySettings.from_env()
    now = time.monotonic()
    if not force and (now - _last_sweep) < settings.sweep_interval_s:
        return 0
    _last_sweep = now
    target = store or get_store()
    records = target.list_audit()
    changed = False
    cutoff = utc_now()
    for record in records:
        if record.status != STATUS_PENDING:
            continue
        expires = parse_iso(record.expires_at or "")
        if expires is not None and expires <= cutoff:
            record.action = ACTION_EXPIRED_DEFAULT_REJECTED
            record.status = STATUS_FINAL
            changed = True
    if changed:
        target.replace_audit(records)
    return int(changed)


# --- CLI ---


def _cli_consolidate() -> int:
    store = get_store()
    entries = store.list_entries()
    buckets: dict[tuple[str, str], list[MemoryEntry]] = {}
    for entry in entries:
        buckets.setdefault((entry.scope, entry.category), []).append(entry)
    total_dropped = 0
    for (scope, category), bucket in buckets.items():
        kept, dropped = consolidate_entries(
            bucket,
            ttl_days=MemorySettings.from_env().entry_ttl_days,
            max_per_key=MemorySettings.from_env().max_entries_per_key,
        )
        total_dropped += len(dropped)
        print(f"{scope}/{category}: kept {len(kept)}, dropped {len(dropped)}")
    print(f"consolidation dry-run complete (dropped {total_dropped})")
    return 0


def _cli_audit() -> int:
    store = get_store()
    for record in store.list_audit():
        print(record.model_dump_json())
    return 0


def main(argv: list[str] | None = None) -> int:
    import sys

    args = list(argv if argv is not None else sys.argv[1:])
    command = args[0] if args else "audit"
    if command == "consolidate":
        return _cli_consolidate()
    if command == "audit":
        return _cli_audit()
    print("Usage: python -m data.pipelines.agent_memory [consolidate|audit]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
