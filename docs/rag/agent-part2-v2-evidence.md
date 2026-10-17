# Part 2 v2 evidence — live runs + evals (PR checklist)

Branch `feature/langgraph-part2-v2` (after PR #40 merge + revert PR #41).
Backend rebuilt from this branch (`docker compose up --build -d backend`);
`AGENT_TOOL_API_URL` set from local `.env` (gitignored). Tool auth has
since moved to a service identity (§9.1): `AGENT_TOOL_CLIENT_ID` /
`AGENT_TOOL_CLIENT_SECRET` (replacing the old pasted
`AGENT_TOOL_API_TOKEN`), auto-renewed via
`data/pipelines/service_token_provider.py`.

## 1. Live `run_agent` battery (real HTTP tools → live APIs)

| # | Question | route | sources_used | Nodes | Result |
|---|----------|-------|--------------|-------|--------|
| 1 | What is the status of ticket 2? | `incidents` | `["incidents"]` | `lookup_incident → answer_from_tool` | `Ticket 2: status=open, category=patient_experience, …` |
| 2 | Is there a charge for cancelling 12 hours in advance? | `rag` | `["rag"]` | `retrieve → generate` | `$50 USD / £40 GBP`, Medicare/Medicaid exempt |
| 3 | According to cancellation policy, status of ticket 2 + no-show fee? | `hybrid_incidents` | `["incidents","rag"]` | `lookup_incident → retrieve → synthesize_hybrid` | Deterministic `status=open` block + policy paragraph |
| 4 | Do we have stock of HCR-PPE-001? | `inventory` | `["inventory"]` | `lookup_inventory → answer_from_tool` | `current_stock=1289` |
| 5 | What is the status of ticket 99999? | `incidents` | `["incidents"]` | `lookup_incident → tool_fallback` | Honest not-found, no invented state |
| 6 | (blank) | — | `[]` | `receive → refuse` | Honest fallback, no tool/RAG calls |

## 2. Live `POST /agent/query` (outer HTTP contract)

- RAG question → `{question, answer}` with `$50 USD / £40 GBP` — HTTP 200.
- Ticket question → `{question, answer}` with live `status=open` — HTTP 200.
- Contract unchanged: `{question, answer}` only.

## 3. Offline suite

```text
pytest tests/pipelines/test_agent_tools.py \
       tests/pipelines/test_agent_graph.py \
       tests/pipelines/test_agent_evals.py \
       tests/pipelines/test_rag.py
→ 71 passed, 1 skipped (live eval needs RUN_LIVE_EVALS=1)
```

`npx tsc --noEmit` in `uis/backoffice` → clean.

## 4. Environment notes (pre-existing, out of scope)

- Prod compose has no volume for TinyDB: every `backend` recreate wipes
  runtime users/incidents **and the `service_clients` registry**, so
  `scripts/seed_service_client.py` must be re-run after a recreate before
  the agent can authenticate. Tracked as delivery-note limitation, not
  fixed here.
- §9 TODO (service identity) **has since been implemented** — the pasted
  user JWT no longer exists; tools authenticate as `svc:langgraph-agent`
  via a short-lived auto-renewed service token (see `agent-graph.md`
  §9.1).
