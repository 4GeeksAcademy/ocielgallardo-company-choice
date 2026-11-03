# OWASP Top 10 Audit Report — HealthCore

**Project:** `ai-eng-cybersecurity-vulnerabilities`  
**Branch:** `feature/owasp-top10-audit`  
**BRIEFING:** [healthcore-BRIEFING.md](./healthcore-BRIEFING.md) §7  
**Evidence rule:** No PHI / identifiable patient data in this report or linked artifacts (synthetic IDs only).

## Scope inventory (BRIEFING §3)

| Component | In fork? | Audit lane note |
| --- | --- | --- |
| Clinical documentation assistant (SOAP) | **N/A** | Not implemented |
| Automated patient referral workflow | **N/A** | Policy KB only; no patient notify engine |
| RAG over clinical/front-desk policies | **Yes** | Agentic + API `/knowledge` |
| Compliance / knowledge agent | **Yes** | LangGraph + WS chat |
| Access audit log system | **N/A** | `services/compliance/` placeholder |
| Clinical KPI SSE dashboard | **N/A** | Supply reporting REST only |
| Staff frontend | **Yes** | `uis/backoffice` |
| RFP HITL agent (related) | **Yes** | Separate B2B pipeline with human gates |

## Three lanes

For each OWASP category: **API/Backend** | **Frontend/Staff UI** | **Agentic/AI**.

---

### A01 Broken Access Control

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| API | Yes | Unauthenticated `POST /api/incidents/analyze`, `GET /api/incidents/results/export` | **Fixed** — require Bearer (`services/app/routers/incidents.py`) |
| API | Yes | Unauthenticated `GET /telemetry/report`; open ingest | **Fixed** — report requires JWT; ingest requires `X-Telemetry-Ingest-Key` when set / mandatory in `APP_ENV=production` |
| API | Yes | Any user could approve any RFP department | **Fixed** — `user_may_approve_department` + admin / `RFP_*_OWNER_EMAIL` |
| API | Yes | Open registration | **Fixed** — `ALLOW_PUBLIC_REGISTRATION` gate |
| Frontend | Yes | Backoffice assumes JWT; no role UI for RFP owners | Residual Medium — document; server enforces |
| Agentic | Yes | Any registered user could open Compliance WS | **Fixed** — staff roles only (`admin`/`manager`) |
| Agentic | Yes | Agent uses shared service token for MCP reads | Residual High — documented; out of scope for this hito |

**Tests:** `tests/test_owasp_access_control.py`, `tests/test_agent_chat_ws.py::test_ws_rejects_non_staff_role`

---

### A02 Cryptographic Failures

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| API | Yes | Secrets via env / `*_FILE`; JWT HS256 for humans; RS256 service JWTs | Acceptable for lab; prod needs TLS edge + `SUPABASE_DB_SSLMODE=require` |
| API | Yes | Auth PEM / `auth.json` could enter image via `COPY data` | **Fixed** — `.dockerignore` excludes `data/process/auth/`, `*.pem`, `auth.json` |
| Frontend | Yes | JWT in `localStorage`; WS token in query string | Residual Medium — documented |
| Agentic | Yes | LLM keys in `.env` (gitignored); BAA/DPA process | Documented in `server-hardening.md` |
| Agentic | Yes | Traces stored raw questions | **Fixed** — traces store `question_chars` only |

---

### A03 Injection

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| API | Yes | FastAPI/Pydantic validation on JSON bodies; SQL via SQLModel | Acceptable |
| Frontend | Partial | React escapes by default | Acceptable |
| Agentic | Yes | Direct + indirect prompt injection | **Fixed** — input refuse + UNTRUSTED_REFERENCE delimiters + output PHI gate |

**Tests:** `tests/test_agent_injection.py` (synthetic `TEST-001`, pattern `123-45-6789`)

---

### A04 Insecure Design

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| API | Yes | TinyDB auth concurrency residual | Residual Medium — not Critical for this deliverable |
| Agentic | Yes | Irreversible clinical note send | **N/A** — SOAP assistant not built; RFP final doc requires HITL |
| Agentic | Yes | BRIEFING §5 human gates | Confirmed for RFP; N/A for missing clinical systems |

---

### A05 Security Misconfiguration

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| API | Yes | Open `/docs` in production | **Fixed** — disabled when `APP_ENV=production` or `DISABLE_API_DOCS=true` |
| API/Infra | Yes | Redis/Qdrant/Flower published on host | **Fixed** — prod compose uses `expose` only |
| Infra | Yes | Containers as root | **Fixed** — `USER app` in prod Dockerfiles |
| Infra | Yes | Host SSH root / wide firewall | **Documented + scripts** — `scripts/hardening/*` (Linux/Codespaces) |
| Frontend | Partial | Prod Next defaults | Acceptable for lab |

Evidence: [server-hardening.md](./server-hardening.md); `docker compose config` should not publish 6379/6333/5555.

---

### A06 Vulnerable and Outdated Components

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| All | Yes | Dependency CVEs may exist in lockfiles | Residual — track via `uv`/`npm audit` in follow-up; not marked Critical for this sign-off without exploit demo |

---

### A07 Identification and Authentication Failures

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| API | Yes | JWT login, password reset, service client credentials | Acceptable baseline |
| API | Partial | JWT not revocable; `is_active` edge cases | Residual Medium |
| Frontend | Yes | Bearer on API; 401 → login redirect | Acceptable |
| Agentic | Yes | WS JWT query param | Residual Medium |

---

### A08 Software and Data Integrity Failures

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| API | Yes | Celery JSON; RFP checkpoints shared volume | Acceptable with internal-only Redis |
| Agentic | Yes | Poisoned RAG chunk as instruction | Mitigated by UNTRUSTED_REFERENCE framing + injection refuse |

---

### A09 Security Logging and Monitoring Failures

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| API | Yes | `api.timing` + principal attribution | Partial |
| Agentic | Yes | Must not log PHI | **Improved** — no raw question in exception logs / traces |
| Access audit log (BRIEFING) | N/A | System not built | N/A |

---

### A10 Server-Side Request Forgery

| Lane | Applies? | Finding | Status |
| --- | --- | --- | --- |
| API | Partial | Agent/MCP backend allowlists for tool hops | Acceptable |
| Agentic | Partial | MCP client fixed URL from env | Acceptable |
| Frontend | No | N/A | N/A |

---

## Critical fixes demonstrated

1. Auth on incidents analyze/export + telemetry report/ingest key  
2. RFP department approval authorization  
3. Registration disable flag  
4. Compose internal-only Redis/Qdrant/Flower + non-root images + docs off in prod  
5. Agent prompt-injection refuse + PHI output sanitize + RAG untrusted delimiters  
6. Linux hardening scripts + runbook (Codespaces evidence path)

## Residual (accepted for follow-up)

- Full RBAC on inventory/suppliers  
- User-scoped MCP tokens  
- Remove JWT from WS query string  
- TinyDB concurrency redesign  
