# Company Knowledge Base (RAG Corpus)

Source documents for the HealthCore knowledge assistant (Milestone 7 — RAG).
`setup()` in `data/process/rag.py` reads `*.md` from this folder
(excluding this README).

## Required source files

Copy them from `00-general-contexts/healthcore/` (TODO: that folder is not
present in this repo yet — no documents indexed until they are provided):

| File | `source_document` value |
| ---- | ----------------------- |
| `healthcore-insurance-coverage.en.md` | `insurance-coverage` |
| `healthcore-appointment-policy.en.md` | `appointment-policy` |
| `healthcore-referral-process.en.md` | `referral-process` |
| `healthcore-new-patient-checklist.en.md` | `new-patient-checklist` |

Each document must yield at least 3 chunks after `setup()`.

## Constraints

- Policies, catalogs, and procedures only — never real patient data.
- No chunk may contain real or realistic-looking PHI (HIPAA / UK GDPR).
- TODO: copy the four source documents, then run
  `uv run python -m data.process.rag` (or `setup()` from Python).
