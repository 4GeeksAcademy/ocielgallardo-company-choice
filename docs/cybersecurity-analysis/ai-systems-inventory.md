# AI Systems Inventory — HealthCore

Source of truth for Identify/Govern. Aligns with [healthcore-BRIEFING.md](./healthcore-BRIEFING.md) §§2–5.  
**No PHI** in this inventory.

## Regulatory note (BRIEFING §2)

| Regime | Notification | Processor agreement |
| --- | --- | --- |
| HIPAA (US clinics) | Up to **60 days** | BAA (incl. LLM vendor) |
| UK GDPR (UK clinics) | **72 hours** to ICO | DPA |

Restricted data: PHI / patient identifiers must never appear in logs, traces, events, or model outputs retained for audit.

## Inventory (built + BRIEFING §3)

| Component | Entrypoints / paths | Owner | Third-party provider | Who owns the control when third party supplies the model/tool | Main risk | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Compliance / knowledge LangGraph agent | `POST /agent/query`, `WS /agent/chat/ws`; `data/pipelines/agent_graph.py`, `agent_guardrails.py` | Compliance — Claire Whitfield | LLM via `LLM_API_*` (Groq/OpenAI-compatible) | HealthCore retains prompt/policy control; vendor supplies model weights/runtime — BAA required before PHI workloads | Direct prompt injection; regulatory hallucination | Implemented |
| RAG over policies/protocols | `POST /knowledge/query`; `data/process/rag.py`, `data/pipelines/rag.py`; Qdrant | Technology — James Osei | Embeddings via `EMBEDDING_API_*`; vectors in Qdrant; LLM for generation | HealthCore owns corpus + retrieval filters; embedding/LLM vendors process query text under BAA/DPA | Indirect prompt injection via poisoned docs | Implemented |
| MCP incidents/inventory tools | `mcps/incidents-inventory-mcp`; `data/pipelines/mcp_client.py` | Technology — James Osei (platform); Compliance oversight on incident content | MCP server is first-party; backend API auth via service JWT | HealthCore owns tool schemas, scopes, and allowlists; no third-party tool host | Excessive agency if write tools exposed to agents | Implemented (agent path is **read-only** lookups) |
| RFP intake / classify / draft | `data/pipelines/rfp_intake/*`; `POST /rfp/...` | Sales/RFP ops with Compliance — Claire Whitfield on compliance sections | LLM via shared `LLM_API_*` | HealthCore owns BRIEFING compliance rules + HITL gates; vendor runs generation | PHI in RFP text; unapproved outbound docs | Implemented |
| RFP approval HITL workflow | `approval_graph.py`; department Approve/Reject APIs + backoffice `/rfp` | Department owners (Revenue / Clinical / Compliance emails) + admins | LangGraph checkpoint store (local Sqlite volume) | HealthCore owns interrupt/resume and approver ACL | Final document without human sign-off | Implemented (human confirmation required) |
| Clinical documentation assistant (SOAP) | — | Clinical Ops — Dr. Marcus Reid | — | — | PHI leakage in notes/logs | N/A (not built in this fork) |
| Automated referral workflow | — | Patient Access — Priya Nair | — | — | Notify/share without human validation | N/A (policy KB only) |
| Access audit log (clinical record access) | — | Compliance — Claire Whitfield | — | — | Log content containing PHI | N/A (placeholder; agent traces are metadata-only) |

## Third-party control summary

- **Model providers (`LLM_API_KEY`, `EMBEDDING_API_KEY`):** HealthCore must keep keys in env/secret files only; never commit. Operational control of prompts, refusal policy, and RAG delimiters stays in-repo.
- **Qdrant / Redis:** Self-hosted in Compose; network exposure is HealthCore’s control (internal-only in prod compose).
- **MCP:** First-party server; scopes and GET-only backend hop are HealthCore controls.

## Related artifacts

- Full NIST mapping: [nist-ai-security-report.md](./nist-ai-security-report.md)
- Protect checklist: [nist-protect-checklist.md](./nist-protect-checklist.md)
