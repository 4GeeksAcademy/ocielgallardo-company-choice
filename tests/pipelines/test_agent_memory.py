"""Unit tests for the agent-memory core (hito 26).

Covers the explicit store contract (in-memory + Redis parity over a fake
client), the single-pending rule, the audit trail, the consolidation policy
(dedupe / cap / TTL / PHI re-screen), relevance selection, and the PHI guard
itself. Everything runs offline — no Redis server, no LLM.

Run:
    python -m pytest tests/pipelines/test_agent_memory.py
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

# Make the repo root importable when pytest is invoked from elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest  # noqa: E402

import data.pipelines.agent_memory as agent_memory  # noqa: E402
import data.pipelines.memory_phi_guard as memory_phi_guard  # noqa: E402
from data.pipelines.agent_memory import (  # noqa: E402
    ACTION_EXPIRED_DEFAULT_REJECTED,
    ACTION_PROPOSED,
    NAMESPACE,
    STATUS_PENDING,
    InMemoryMemoryStore,
    MemorySettings,
    RedisMemoryStore,
    StoreError,
    consolidate_entries,
    make_audit,
    make_entry,
    make_pending,
    maybe_sweep,
    normalize_category,
    normalize_scope,
    redact_message,
    select_relevant,
    _assert_agent_namespace,
)


def _settings(**overrides) -> MemorySettings:
    base = dict(
        backend="memory",
        redis_url="redis://localhost:6379/0",
        entry_ttl_days=180,
        max_entries_per_key=20,
        audit_max=1000,
        audit_ttl_days=90,
        pending_ttl_hours=168,
        sweep_interval_s=600,
    )
    base.update(overrides)
    return MemorySettings(**base)


class FakeRedis:
    """Minimal Redis surface used by ``RedisMemoryStore`` (offline parity)."""

    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.sets: dict[str, set[str]] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.strings[key] = value
        if ex is not None:
            self.ttls[key] = ex

    def delete(self, *keys: str) -> None:
        for key in keys:
            self.strings.pop(key, None)
            self.lists.pop(key, None)
            self.sets.pop(key, None)
            self.ttls.pop(key, None)

    def rpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).append(value)

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        items = self.lists.get(key, [])
        length = len(items)
        if start < 0:
            start = max(length + start, 0)
        if end < 0:
            end = length + end
        return items[start : end + 1]

    def ltrim(self, key: str, start: int, end: int) -> None:
        self.lists[key] = self.lrange(key, start, end)

    def expire(self, key: str, seconds: int) -> None:
        self.ttls[key] = seconds

    def sadd(self, key: str, member: str) -> None:
        self.sets.setdefault(key, set()).add(member)

    def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))


@pytest.fixture(params=["memory", "redis"])
def store(request) -> InMemoryMemoryStore | RedisMemoryStore:
    if request.param == "memory":
        return InMemoryMemoryStore(_settings())
    return RedisMemoryStore(_settings(), client=FakeRedis())


# --- PHI guard ---


@pytest.mark.parametrize(
    "text",
    [
        "The patient Johnson cancelled tomorrow's appointment, please note it",
        "El paciente García canceló su cita de mañana",
        "Save MRN 1234567 for later",
        "date of birth 03/04/1981",
        "fecha de nacimiento: 12/05/1975",
        "SSN 123-45-6789",
        "NHS number AB12345C",
        "insurance number 987654321",
        "member id 55555123456",
        "lab results came back positive last week",
        "resultado de laboratorio anormal",
        "clinical note: patient reports mild fever",
        "diagnosis was type 2 diabetes",
        "acct number 123456789012",
    ],
)
def test_phi_guard_blocks_candidates(text: str) -> None:
    verdict = memory_phi_guard.scan(text)
    assert verdict.allowed is False
    assert verdict.reasons  # codes only, never the matched text


@pytest.mark.parametrize(
    "text",
    [
        "In Manchester the internal referral process now goes through the coordinator first",
        "The Miami clinic now closes at 11pm on weekends",
        "The referral system fails on Monday mornings because of the nightly batch",
        "Weekly report for Diane Foster must include vacancies by role",
        "Stock of HCR-PPE-001 is 1289 boxes",
        "Ticket 2 is open since 2024-01-17",
        "Patient not informed of appointment reschedule",
        "No-show alerts spike when the reminder job fails",
    ],
)
def test_phi_guard_allows_operational_facts(text: str) -> None:
    assert memory_phi_guard.scan(text).allowed is True


def test_phi_guard_never_returns_matched_text() -> None:
    verdict = memory_phi_guard.scan("The patient Johnson cancelled the visit")
    assert "Johnson" not in verdict.reasons
    assert set(verdict.reasons) <= set(memory_phi_guard.PHI_REASONS)


def test_scan_proposal_merges_fields() -> None:
    verdict = memory_phi_guard.scan_proposal(
        {"scope": "austin", "category": "hours", "fact": "closes at 10pm", "reason": "ok"}
    )
    assert verdict.allowed is True
    dirty = memory_phi_guard.scan_proposal(
        {"scope": "austin", "category": "hours", "fact": "about patient Johnson", "reason": ""}
    )
    assert dirty.allowed is False


def test_redact_message_hides_phi() -> None:
    safe, redacted = redact_message("Remember the patient Johnson case")
    assert redacted is True
    assert "Johnson" not in safe
    safe, redacted = redact_message("Manchester clinic opens at 8am")
    assert redacted is False
    assert "Manchester" in safe


# --- Normalization / selection ---


def test_normalize_scope_and_category() -> None:
    assert normalize_scope("  Manchester Clinic! ") == "manchester clinic"
    assert normalize_scope("") == "network"
    assert normalize_category("HOURS") == "hours"
    assert normalize_category("random") == "other"


def test_select_relevant_ignores_unrelated_entries() -> None:
    now = agent_memory.utc_now()
    entries = [
        make_entry(scope="manchester", category="procedure", fact="referrals go via the coordinator", now=now),
        make_entry(scope="austin", category="hours", fact="closes at 10pm on Fridays", now=now),
    ]
    picked = select_relevant(entries, "What is the referral process in Manchester?")
    assert [entry.fact for entry in picked] == ["referrals go via the coordinator"]
    assert select_relevant(entries, "nothing in common here at all") == []


# --- Store contract (both backends) ---


def test_pending_is_single_per_session(store) -> None:
    first = make_pending(session_id="s1", scope="austin", category="hours", fact="closes at 10pm")
    second = make_pending(session_id="s1", scope="austin", category="hours", fact="opens at 9am")
    assert store.set_pending(first) is True
    assert store.set_pending(second) is False
    assert store.get_pending("s1").fact == "closes at 10pm"
    store.clear_pending("s1")
    assert store.get_pending("s1") is None
    assert store.set_pending(second) is True


def test_pending_expires_and_disappears(store) -> None:
    stale = make_pending(
        session_id="s1",
        scope="austin",
        category="hours",
        fact="closes at 10pm",
        now=agent_memory.utc_now() - timedelta(hours=200),
        pending_ttl_hours=168,
    )
    # make_pending with a past "now" still stamps a future expiry relative to
    # that now; force an already-expired proposal instead.
    stale.expires_at = agent_memory.utc_now().isoformat()
    assert store.set_pending(stale) is True
    assert store.get_pending("s1") is None


def test_entries_and_audit_roundtrip(store) -> None:
    entry = make_entry(scope="austin", category="hours", fact="closes at 10pm on Fridays")
    dropped = store.put_entry(entry)
    assert dropped == []
    assert [item.fact for item in store.list_entries()] == ["closes at 10pm on Fridays"]

    store.append_audit(make_audit(ACTION_PROPOSED, scope="austin", category="hours", fact=entry.fact))
    audit = store.list_audit()
    assert len(audit) == 1
    assert audit[0].action == ACTION_PROPOSED
    assert audit[0].fact == entry.fact


def test_put_entry_merges_duplicates(store) -> None:
    first = make_entry(scope="austin", category="hours", fact="Closes at 10pm on Fridays.")
    second = make_entry(scope="austin", category="hours", fact="closes at 10pm on fridays")
    store.put_entry(first)
    store.put_entry(second)
    entries = store.list_entries()
    assert len(entries) == 1
    assert any(record.action == "consolidated" for record in store.list_audit())


def test_put_entry_enforces_cap(store) -> None:
    for index in range(25):
        store.put_entry(
            make_entry(
                scope="austin",
                category="hours",
                # Distinct token sets so consolidation's near-duplicate merge
                # does not collapse them before the cap applies.
                fact=(
                    "opening hours guideline revision "
                    f"alpha{index} bravo{index} charlie{index}"
                ),
            )
        )
    entries = store.list_entries()
    assert len(entries) == store.settings.max_entries_per_key


def test_expired_entries_are_hidden(store) -> None:
    entry = make_entry(scope="austin", category="hours", fact="closes at 10pm")
    entry.expires_at = (agent_memory.utc_now() - timedelta(days=1)).isoformat()
    store.put_entry(entry)
    assert store.list_entries() == []


def test_namespace_guard_rejects_knowledge_keys() -> None:
    _assert_agent_namespace(f"{NAMESPACE}:entries:austin:hours")
    with pytest.raises(StoreError):
        _assert_agent_namespace("healthcore_knowledge")
    with pytest.raises(StoreError):
        _assert_agent_namespace("other:memory:entries")


def test_every_store_key_stays_in_agent_namespace(store) -> None:
    store.put_entry(make_entry(scope="austin", category="hours", fact="closes at 10pm"))
    store.set_pending(make_pending(session_id="s1", scope="austin", category="hours", fact="x"))
    store.append_audit(make_audit(ACTION_PROPOSED, scope="austin", category="hours"))
    client = getattr(store, "_client", None)
    if client is None:  # in-memory: inspect internal buckets
        keys = list(store._entries.keys()) + [f"{NAMESPACE}:pending:s1", f"{NAMESPACE}:audit"]
    else:  # fake redis
        keys = list(client.strings) + list(client.lists) + list(client.sets)
    assert keys
    for key in keys:
        assert key.startswith(NAMESPACE)
        assert "knowledge" not in key


# --- Consolidation policy ---


def test_consolidate_drops_expired_duplicates_and_cap() -> None:
    now = agent_memory.utc_now()
    expired = make_entry(scope="austin", category="hours", fact="old fact", now=now, ttl_days=1)
    expired.expires_at = (now - timedelta(days=1)).isoformat()
    keep_newest = make_entry(scope="austin", category="hours", fact="closes at 10pm", now=now)
    older_dup = make_entry(
        scope="austin", category="hours", fact="Closes at 10pm.", now=now - timedelta(days=5)
    )
    extras = [
        make_entry(
            scope="austin",
            category="hours",
            fact=f"schedule note alpha{index} bravo{index} charlie{index}",
            now=now,
        )
        for index in range(20)
    ]
    kept, dropped = consolidate_entries(
        [expired, older_dup, keep_newest, *extras],
        now=now,
        ttl_days=180,
        max_per_key=5,
    )
    reasons = {item["reason"] for item in dropped}
    assert "expired" in reasons
    assert "duplicate" in reasons
    assert "cap" in reasons
    assert len(kept) == 5
    # Newest duplicate wins.
    assert keep_newest.id in {entry.id for entry in kept}


def test_consolidate_rescreens_phi() -> None:
    now = agent_memory.utc_now()
    poisoned = make_entry(scope="austin", category="hours", fact="closes at 10pm", now=now)
    poisoned.fact = "remember patient Johnson cancelled"  # bypass write-time screen
    kept, dropped = consolidate_entries([poisoned], now=now)
    assert kept == []
    assert dropped[0]["reason"] == "phi"


# --- Sweep: silence is a recorded rejection ---


def test_sweep_marks_stale_pending_audit() -> None:
    store = InMemoryMemoryStore(_settings())
    record = make_audit(
        ACTION_PROPOSED,
        session_id="s1",
        proposal_id="p1",
        scope="austin",
        category="hours",
        status=STATUS_PENDING,
        expires_at=(agent_memory.utc_now() - timedelta(days=1)).isoformat(),
    )
    store.append_audit(record)
    changed = maybe_sweep(store, force=True)
    assert changed == 1
    swept = store.list_audit()[0]
    assert swept.action == ACTION_EXPIRED_DEFAULT_REJECTED
    assert swept.status == "final"


# --- Factory ---


def test_get_store_defaults_to_in_memory(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MEMORY_BACKEND", "memory")
    agent_memory.reset_store()
    store = agent_memory.get_store()
    assert isinstance(store, InMemoryMemoryStore)
    agent_memory.reset_store()
