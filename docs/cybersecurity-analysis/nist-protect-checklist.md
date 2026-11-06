# NIST Protect Checklist — HealthCore (Hito 29)

Aligned with BRIEFING §§2–6. Complements the [OWASP report](./owasp-top10-report.md).  
**No PHI** in this document or test artifacts.

## Separate regulatory regimes

| Topic | HIPAA (US) | UK GDPR |
| --- | --- | --- |
| Breach notification window | Up to **60 days** | **72 hours** to the ICO |
| Authority | HHS / covered entity obligations | ICO |
| Processor agreement | Business Associate Agreement (BAA) with vendors (incl. LLM) | Data Processing Agreement (DPA) |
| Patient rights / access | HIPAA individual rights | UK GDPR data subject rights |

These are **not** a single global policy — incident playbooks must branch by clinic country.

## AI inventory + owners (BRIEFING §3)

| Component | Owner (role) | Status in fork |
| --- | --- | --- |
| Clinical documentation assistant | Clinical Ops — Dr. Marcus Reid | N/A (not built) |
| Automated referral workflow | Patient Access — Priya Nair | N/A (policy KB only) |
| RAG over protocols/policies | Technology — James Osei | Implemented (front-desk policies) |
| Compliance agent | Compliance — Claire Whitfield | Implemented (knowledge/LangGraph chat) |
| Access audit log system | Compliance — Claire Whitfield | N/A (placeholder) |

## Protect checklist items

- [x] **HIPAA vs UK GDPR treated separately** (table above).
- [x] **Inventory with owners** (table above).
- [x] **Prompt injection demo blocked** — `tests/test_agent_injection.py` (synthetic `TEST-001`; no real SSN).
- [x] **Indirect injection framing** — `<<<UNTRUSTED_REFERENCE_*>>>` in `data/pipelines/rag.py`.
- [x] **Output PHI-like gate** — `sanitize_agent_output` refuses SSN-like / PHI-pattern answers.
- [x] **Irreversible actions (§5)** — SOAP sign/send and patient lab notify **N/A** (not built). RFP final document requires HITL (`approval_graph`). Sharing history cross-clinic without formal referral: N/A (no patient record share API).
- [x] **No PHI in logs / traces (Protect)** — agent traces store `question_chars` only; agent exception logs avoid raw question text; audit artifacts use synthetic IDs.

## Server Protect controls

See [server-hardening.md](./server-hardening.md): non-root deploy user, `PermitRootLogin no`, UFW 22/80/443, Compose internal Redis/Qdrant/Flower.
