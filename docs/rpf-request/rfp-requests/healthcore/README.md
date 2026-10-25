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
