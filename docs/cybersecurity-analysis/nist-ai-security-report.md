# NIST AI Security Report — HealthCore (Hito 29)

Maps current AI systems to NIST CSF functions. Regulatory framing from [healthcore-BRIEFING.md](./healthcore-BRIEFING.md) §2 — **HIPAA (US)** and **UK GDPR (UK) are separate regimes**, not one global policy.

**No PHI** in this report or linked test artifacts (synthetic IDs only).

Companion docs: [ai-systems-inventory.md](./ai-systems-inventory.md), [nist-protect-checklist.md](./nist-protect-checklist.md), [owasp-top10-report.md](./owasp-top10-report.md).

---

## Govern

**Concrete action (this cycle):** Publish owner matrix + dual-regime policy in the [AI inventory](./ai-systems-inventory.md); enforce BRIEFING non-negotiable rule — audit that an action occurred, never store clinical content in traces.

- Owners assigned per component (Claire Whitfield / James Osei / Marcus Reid / Priya Nair as in BRIEFING §3).
- Third-party model/tool control responsibility documented (HealthCore retains prompts, scopes, HITL; vendors supply runtime under BAA/DPA).

---

## Identify

**Concrete action (this cycle):** Complete inventory of built agents, RAG, MCP, RFP workflows plus BRIEFING §3 N/A items with risks.

See [ai-systems-inventory.md](./ai-systems-inventory.md). Highest active risks on implemented surfaces: direct prompt injection on `/agent/query`, indirect injection via RAG corpus, LLM cost loops without rate limits (mitigated this cycle), WS JWT-in-query residual.

---

## Protect

**Concrete action (this cycle):** Keep injection/PHI guardrails; add **rate limiting** on `POST /agent/query`; keep secrets in env/`*_FILE`; UNTRUSTED RAG delimiters; typed MCP tool outputs; RFP HITL for irreversible approvals.

| Control | Evidence |
| --- | --- |
| Input sanitization / injection refuse | `data/pipelines/agent_guardrails.py`; `tests/test_agent_injection.py` |
| System vs user / untrusted context | `<<<UNTRUSTED_REFERENCE_*>>>` in `data/pipelines/rag.py` |
| Secrets | `.env.example` — `LLM_API_KEY`, `EMBEDDING_API_KEY`, service client secrets; no hardcoded keys |
| Rate limit (LLM endpoint) | `services/app/core/rate_limit.py` on `POST /agent/query`; `tests/test_agent_rate_limit.py` |
| Tool output validation | Pydantic `IncidentToolOutput` / `InventoryToolOutput` before formatting (`agent_tools.py`, `agent_graph._tool_facts_text`) |
| Irreversible actions (BRIEFING §5) | SOAP sign/send & patient notify **N/A** (not built). RFP finalization requires human Approve via `approval_graph` |
| No PHI in logs | Traces use `question_chars`; RAG/agent exception logs avoid raw question text |

---

## Detect

**Concrete action (this cycle):** Treat `refuse_security` spans in agent traces and HTTP **429** rate-limit responses as abuse signals; retain telemetry `auth_failure_rate` for access anomalies.

| Signal | Where |
| --- | --- |
| Injection blocked | Trace span `refuse_security` via `get_trace(trace_id)` |
| Rate abuse | Warning log `Agent query rate limited (user_id=...)` + 429 |
| Auth failures | Telemetry report metric `auth_failure_rate` |

---

## Respond

**Concrete action (this cycle):** Dual-track incident playbook (BRIEFING §2) — no PHI in tickets.

| Clinic country | Notify | Deadline |
| --- | --- | --- |
| United States | Covered-entity / HIPAA breach process | Up to **60 days** |
| United Kingdom | ICO (+ other UK GDPR obligations) | **72 hours** from awareness |

Steps (metadata-only):

1. Disable or rate-tighten affected LLM endpoints (`AGENT_QUERY_RATE_LIMIT`).
2. Rotate `LLM_API_KEY` / service client secrets from vault/env files.
3. Preserve agent `trace_id` + spans (no raw prompts/PHI).
4. Branch notification timeline by clinic country — never collapse HIPAA and UK GDPR into one SLA.

---

## Recover

**Concrete action (this cycle):** Document restoration path for AI-adjacent services.

1. `docker compose up` — recreate `backend`, `mcp`, worker; Redis/Qdrant remain internal-only in prod compose.
2. Restore RFP HITL continuity from volume `rfp_langgraph_checkpoints` (`/app/data/process/rfp`).
3. Re-seed service clients if secrets rotated: `scripts/seed_service_client.py`.
4. Re-run `tests/test_agent_injection.py` and `tests/test_agent_rate_limit.py` as smoke before reopening staff traffic.

---

## Residual gaps (not fixed this cycle)

| Gap | Risk | Proposed mitigation | Priority |
| --- | --- | --- | --- |
| WebSocket JWT passed in query string (`/agent/chat/ws?token=`) | Token leakage via proxy/access logs | Prefer `Sec-WebSocket-Protocol` or short-lived ticket exchange | P1 |
| In-memory rate limiter (single process) | Limit bypass across replicas | Shared Redis token bucket for `/agent/query` | P2 |
| Clinical SOAP / referral / PHI access-audit systems N/A | BRIEFING inventory incomplete in product | Build with physician HITL + metadata-only audit before production PHI | P1 (product) |
| Regex routing on compliance agent | Mis-route / weaker intent control | LLM classifier with guardrails still applied first | P3 |

---

## Acceptance mapping

| Rubric item | Status |
| --- | --- |
| Inventory with owners | [ai-systems-inventory.md](./ai-systems-inventory.md) |
| No hardcoded credentials | Env/vault pattern; verified in Protect |
| Reproducible prompt-injection block | `tests/test_agent_injection.py` |
| Rate limit on model endpoint | `tests/test_agent_rate_limit.py` |
| Agent decision logging | LangGraph traces (`question_chars` + spans) |
| Irreversible actions need human confirm | RFP HITL; §5 clinical actions N/A |
| Six NIST functions with concrete actions | Sections above |
| BRIEFING regulatory framing | HIPAA 60d vs UK GDPR 72h ICO throughout |
