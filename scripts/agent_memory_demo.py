"""Offline demo of the agent-memory loop (hito 26 evidence, no network).

Runs the real graph, the real memory store (in-process backend), the real
PHI screen and the real audit trail with only the LLM seams scripted, so the
two required cycles can be reproduced anywhere — no Redis, no Qdrant, no API
keys. This is the same seam-pinning the test suite uses
(``tests/pipelines/test_agent_graph_memory.py``).

Cycles shown:
  1. approved  — proposal → user approval → the fact answers a later question
  2. rejected  — proposal → user rejection → the memory stays unchanged
  plus a PHI attempt that is refused before anything is shown or stored.

Run:
    uv run python scripts/agent_memory_demo.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.environ.setdefault("AGENT_MEMORY_BACKEND", "memory")

import data.pipelines.agent_graph as agent_graph  # noqa: E402
import data.pipelines.agent_memory as agent_memory  # noqa: E402
import data.pipelines.memory_proposer as memory_proposer  # noqa: E402
import data.pipelines.rag as rag_pipeline  # noqa: E402

MANCHESTER_FACT = (
    "The internal referral process now goes through the coordinator "
    "before the specialist (changed last quarter)"
)

_DECISION = {"label": "unrelated", "edited_fact": None}
_GENERATE_SCRIPT: list[tuple[str, dict | None]] = []


def _fake_retrieve(question: str, **kwargs) -> list[dict]:
    return [
        {
            "company": "healthcore",
            "source_document": "referral-policy",
            "section": "Internal referrals",
            "language": "en",
            "chunk_index": 0,
            "text": "Internal referrals are reviewed by the clinic coordinator.",
        }
    ]


def _fake_generate(question, context, *, memory=None):
    if _GENERATE_SCRIPT:
        return _GENERATE_SCRIPT.pop(0)
    remembered = "; ".join(item["fact"] for item in (memory or []))
    if remembered:
        return f"(policy answer using memory: {remembered})", None
    return "(plain policy answer)", None


def _fake_classify(proposal, message):
    return dict(_DECISION)


def _turn(question: str, session: str) -> dict:
    result = agent_graph.run_agent(question, session_id=session)
    trace = agent_graph.get_trace(result["trace_id"])
    print(f"\n> user: {question}")
    print(f"< agent: {result['answer']}")
    print(f"  [route={result.get('route')} memory={trace['memory']}]")
    return result


def _dump_store(store: agent_memory.InMemoryMemoryStore, title: str) -> None:
    print(f"\n--- {title} ---")
    entries = store.list_entries()
    print(f"entries: {len(entries)}")
    for entry in entries:
        print(f"  - [{entry.scope}|{entry.category}] {entry.fact}")
    print("audit:")
    for record in store.list_audit():
        fact = record.fact or ("(omitted)" if record.phi_reasons else "-")
        print(
            f"  - {record.action:<28} decision={record.decision or '-':<10} "
            f"fact={fact!r} phi_reasons={record.phi_reasons}"
        )


def main() -> int:
    store = agent_memory.InMemoryMemoryStore()
    agent_memory.set_store(store)
    rag_pipeline.retrieve = _fake_retrieve
    rag_pipeline.generate_answer_with_proposal = _fake_generate
    memory_proposer.classify_decision = _fake_classify

    session = "demo-session"

    print("=" * 72)
    print("CYCLE 1 — approved: remembered fact answers a later question")
    print("=" * 72)
    _GENERATE_SCRIPT.append(
        (
            "Referrals now route through the clinic coordinator first.",
            {
                "scope": "manchester",
                "category": "procedure",
                "fact": MANCHESTER_FACT,
                "reason": "user corrected the referral flow",
            },
        )
    )
    _turn("In Manchester the referral process changed last quarter.", session)
    _dump_store(store, "after proposal (pending, nothing stored yet)")

    _DECISION["label"] = "approve"
    _turn("Yes, save that for next time.", session)
    _dump_store(store, "after approval (fact consolidated)")

    _turn("How do internal referrals work in Manchester now?", session)
    _DECISION["label"] = "unrelated"

    print("\n" + "=" * 72)
    print("CYCLE 2 — rejected: the memory stays unchanged")
    print("=" * 72)
    _GENERATE_SCRIPT.append(
        (
            "The Austin clinic now closes at 11pm on Fridays.",
            {
                "scope": "austin",
                "category": "hours",
                "fact": "The Austin clinic now closes at 11pm on Fridays",
                "reason": "user corrected the closing hour",
            },
        )
    )
    _turn("The Austin clinic now closes at 11pm on Fridays, not 10pm.", session)
    _DECISION["label"] = "reject"
    _turn("No, don't store that.", session)
    _dump_store(store, "after rejection (no new entry, audit keeps the decision)")

    print("\n" + "=" * 72)
    print("PHI ATTEMPT — refused before it is shown or stored")
    print("=" * 72)
    _DECISION["label"] = "unrelated"
    _GENERATE_SCRIPT.append(
        (
            "Noted.",
            {
                "scope": "austin",
                "category": "incident_pattern",
                "fact": "The patient Johnson cancellation was caused by the reminder job",
                "reason": "user asked to remember it",
            },
        )
    )
    _turn(
        "Please remember that the patient Johnson cancellation was the reminder job.",
        session,
    )
    _dump_store(store, "final store state")

    agent_memory.reset_store()
    print("\nDone. Automated coverage: tests/pipelines/test_agent_memory.py +")
    print("tests/pipelines/test_agent_graph_memory.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
