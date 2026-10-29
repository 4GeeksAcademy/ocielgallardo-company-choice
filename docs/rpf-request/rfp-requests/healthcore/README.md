# HealthCore sample RFP PDFs (Part 1 intake)

Upload these through the backoffice **RFP Intake** page (`/rfp`). Intake stores copies under `data/raw/rfp/` — do not treat them as pre-seeded inventory.

| File | Expected result |
|------|-----------------|
| `healthcore-request-1-formal-meridian.pdf` | Accept → `intake_complete` (US, BAA, USD) |
| `healthcore-sample-rfp-meridian.pdf` | Same Meridian happy-path sample (alternate PDF); Accept → `intake_complete` |
| `healthcore-request-2-informal-thames.pdf` | Accept → `intake_complete` (UK, DPA, GBP) |
| `healthcore-request-3-invalid-ehr-vendor.pdf` | Reject → `discarded` (vendor pitch) |
| `healthcore-request-phi-case.pdf` | Accept or process with **PHI flag/redact** — never show raw patient name/diagnosis in UI |

If the curriculum ships official filenames (`healthcore-request-1.pdf` etc.), drop them here alongside these stand-ins.

## Design Q&A (Part 1)

**Unknown department mentioned in the RFP?**  
Orchestrator records an open question under Revenue; it does **not** spawn invent workers. Only `revenue`, `clinical`, `compliance` run.

**What does each worker receive?**  
Shared metadata + department-relevant Markdown extracts (not the full PDF). Missing volume/budget → open questions; never invent headcount or PHI.

**How do we decide “not an RFP”?**  
Classifier (heuristics + optional LLM). Vendor/EHR sales pitches → `discarded` with reason. False negatives: prefer accepting informal partnership emails when signals are present; unit fixtures cover formal / informal / invalid.

**Contradictory workers?**  
Synthesizer lists soft conflicts in the Sales summary; no free-form LLM arbitration in Part 1 (Part 3 arbiter comes later).

**Async + mid-pipeline failure?**  
Celery task `rfp.intake_run`. Ticket stays `analyzing` with `last_error`; UI offers **Retry** (`POST /rfp/tickets/{id}/retry`). Other tickets are unaffected.

## Parts 2–3 (draft → HITL → final document)

Happy-path UI check on `/rfp` (Compose stack up):

1. Upload Meridian PDF → wait **Intake complete**.
2. **Generate draft** → wait **Under evaluation** / `ready_for_part3` (Part 2 is Celery `rfp.draft_run`; use **Retry drafting** if stuck).
3. **Start approvals** → `waiting_for_approval` (API starts the LangGraph HITL graph **sync** so interrupts live with Approve).
4. **Approve** revenue / clinical / compliance (any order) → **Done** + final markdown.

Notes:

- Compose mounts shared volume `rfp_langgraph_checkpoints` on `backend` and `worker` at `/app/data/process/rfp` (SqliteSaver).
- Each Start/Retry bumps `approval_graph_generation` → thread `rfp-{ticket_id}-gN`.
- **Retry approvals** when `last_error` is set, or when all departments are approved but no final document exists.
- Synthesizer requires all three approvals and **no section-level PHI**. Metadata `contains_phi` alone does not block after Compliance approves and drafts are clean.
- Reproducible without UI: `uv run python scripts/run_rfp_approval_e2e.py`; smoke DB path: `scripts/run_rfp_milestone9_smoke.py`.
