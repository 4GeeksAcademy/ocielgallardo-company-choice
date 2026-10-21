# Agent Memory — Loop Evidence (Hito 26, Part 1)

Offline, reproducible evidence for the two required memory cycles (approved
and rejected), plus the HealthCore-mandated PHI refusal. The real graph, the
real memory store, the real PHI screen and the real audit trail run as in
production; only the LLM seams are scripted. The design/architecture
justification lives in the milestone design document and the PR description.

## How to reproduce

```bash
# scripted demo (no Redis, no Qdrant, no API keys)
uv run python scripts/agent_memory_demo.py

# automated coverage
python -m pytest tests/pipelines/test_agent_memory.py \
                 tests/pipelines/test_agent_graph_memory.py
```

The suite result for this branch: **203 passed, 1 skipped** in
`tests/pipelines/` (full repo suite: **312 passed, 1 skipped**), executed via
the documented `subst W:` workaround for the Windows MAX_PATH/langsmith
limitation.

---

## Cycle 1 — approved: the remembered fact answers a later question

Turn 1 — the interaction produces a durable operational correction, so the
single structured call returns the answer **and** `propuesta_memoria`; the
proposal is asked inside the same answer and nothing is written yet:

```text
> user: In Manchester the referral process changed last quarter.
< agent: Referrals now route through the clinic coordinator first.

Do you want me to remember this for next time? Reply yes, no, or correct me.
  [route=rag memory={'n_memory_facts': 0, 'resolution': 'none', 'proposal': 'proposed'}]

--- after proposal (pending, nothing stored yet) ---
entries: 0
audit:
  - proposed   decision=-   fact='The internal referral process now goes through the coordinator before the specialist (changed last quarter)'
```

Turn 2 — the next message is classified against the pending proposal with an
explicit label (`approve`), re-screened for PHI, consolidated into the store
(dedupe + cap policy applied by `put_entry`) and the audit records the
authorization:

```text
> user: Yes, save that for next time.
< agent: (plain policy answer)

Saved to my memory.
  [route=rag memory={'n_memory_facts': 0, 'resolution': 'approved', 'proposal': 'none'}]

--- after approval (fact consolidated) ---
entries: 1
  - [manchester|procedure] The internal referral process now goes through the coordinator before the specialist (changed last quarter)
audit:
  - proposed   decision=-       fact='The internal referral process …'
  - approved   decision=approve fact='The internal referral process …'
```

Turn 3 — a later question loads the approved fact from the store
(`select_relevant` → `memory_context`) and it reaches the generation prompt,
so the answer is personalized by what was remembered:

```text
> user: How do internal referrals work in Manchester now?
< agent: (policy answer using memory: The internal referral process now goes through the coordinator before the specialist (changed last quarter))
  [route=rag memory={'n_memory_facts': 1, 'resolution': 'none', 'proposal': 'none'}]
```

## Cycle 2 — rejected: the memory stays unchanged

Turn 1 — a second correction is proposed the same way (note: the Manchester
fact is still available, `n_memory_facts=1`):

```text
> user: The Austin clinic now closes at 11pm on Fridays, not 10pm.
< agent: The Austin clinic now closes at 11pm on Fridays.

Do you want me to remember this for next time? Reply yes, no, or correct me.
  [route=rag memory={'n_memory_facts': 1, 'resolution': 'none', 'proposal': 'proposed'}]
```

Turn 2 — the user rejects it: classified `reject`, the pending slot is
closed, **no entry is written**, and the rejection itself is audited:

```text
> user: No, don't store that.
< agent: (plain policy answer)

Understood — I won't store it.
  [route=rag memory={'n_memory_facts': 0, 'resolution': 'rejected', 'proposal': 'none'}]

--- after rejection (no new entry, audit keeps the decision) ---
entries: 1            # unchanged: only the approved Manchester fact
audit:
  - proposed   decision=-         fact='The Austin clinic now closes at 11pm on Fridays'
  - rejected   decision=reject    fact='-'
```

Silence / ambiguity / topic change follow the same path as a rejection
(`default_rejected` in the audit, no note bolted onto the answer, pending
cleared). A pending proposal nobody answers expires after
`AGENT_MEMORY_PENDING_TTL_HOURS` (default 7 days) and the sweep records it
as `expired_default_rejected`.

## PHI attempt — refused before it is shown or stored

HealthCore's non-negotiable rule: a proposal containing patient-identifying
or clinical content never reaches the user as a "want me to remember this?"
question, is never persisted, and the user is told explicitly:

```text
> user: Please remember that the patient Johnson cancellation was the reminder job.
< agent: Noted.

I can't save that to my memory: it looks like it contains patient-identifying
or clinical information (HIPAA / UK GDPR). Nothing was stored. Operational
facts without patient data are fine to remember.
  [route=rag memory={'n_memory_facts': 0, 'resolution': 'none', 'proposal': 'rejected_phi'}]

--- final store state ---
entries: 1
audit:
  …
  - rejected_phi   decision=-   fact='(omitted)'   phi_reasons=['patient_name']
```

The audit keeps the **reason code only** — the matched text is never stored
or logged, and the same screen runs again before any consolidated version is
written back.

---

## Self-evaluation checklist (implemented criteria)

Interactions that **do** generate a proposal (briefing examples, covered by
`test_memorable_interactions_propose_inside_the_answer`):

1. "In Manchester the internal referral process now passes through the
   coordinator before the specialist — it changed last quarter."
2. "That elevated no-show alert in the Austin clinic was a road closure that
   week, not a real problem with the reminder program."
3. "The weekly report for Diane Foster must include vacancies by role, not
   only by clinic — she asked two weeks ago."

Interactions that **must not** generate a proposal (parametrized in
`test_non_memorable_interactions_propose_nothing`):

1. "What was the no-show rate this week?" — one-off lookup; the data lives
   in the dashboard/telemetry, not in agent memory.
2. "Thanks, that answers my question." — conversation closing, nothing new.
3. "Can you translate this into English for the weekly report?" — single-use
   task, no durable operational fact.

Plus the PHI case: asking to remember patient-specific content is refused
explicitly (not silently ignored).

## Consolidation / cleanup policy (implemented defaults)

| Knob | Default | Behaviour |
|------|---------|-----------|
| `AGENT_MEMORY_TTL_DAYS` | 180 | Entry expiry; expired entries are hidden from reads and dropped on consolidation |
| `AGENT_MEMORY_MAX_ENTRIES_PER_KEY` | 20 | Cap per clinic+category bucket; newest entries win |
| `AGENT_MEMORY_AUDIT_MAX` | 1000 | Audit ring buffer (every proposal outcome, approved or not) |
| `AGENT_MEMORY_AUDIT_TTL_DAYS` | 90 | Sliding retention for the audit trail |
| `AGENT_MEMORY_PENDING_TTL_HOURS` | 168 | A proposal the user never answers is discarded and recorded as `expired_default_rejected` |

Dedupe merges normalized-identical or near-duplicate facts (Jaccard ≥ 0.9;
the newest version wins), and every kept fact is re-screened for PHI before
the consolidated bucket is written back. CLI: `python -m
data.pipelines.agent_memory consolidate|audit`.

## Store separation

All keys live under the `agent:memory:*` namespace (`pending`, `entries`,
`audit`, `index`). Nothing in this milestone writes to the Qdrant
`healthcore_knowledge` collection — RAG stays a read-only tool.
`_assert_agent_namespace()` enforces that at runtime and
`test_namespace_guard_rejects_knowledge_keys` pins it in tests.
