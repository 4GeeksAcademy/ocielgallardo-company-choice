# 📦 `data/raw` — landing zone for original data

This folder holds **untransformed** company datasets: dumps, exports, and sample files that pipelines or analysis tools consume as-is.

Think of it as the loading dock — data arrives here before anything cleans, validates, or aggregates it.

## Purpose

- Keep a clear boundary between **raw** input and processed outputs (`data/process/`).
- Give scripts and services a stable place to find sample / source files.
- Document origin, format, and privacy constraints for every dataset you drop here.

## 📂 Current datasets

| File | What it is | Notes |
| --- | --- | --- |
| `incidents-healthcore.csv` | Patient incident reports sample for HealthCore | UTF-8, comma-separated, header row. Used by `scripts/analyze.py` via `services/incidents-analysis`. |

### 🔒 Privacy (non-negotiable)

`incidents-healthcore.csv` includes `patient_id` values protected under **HIPAA** (US) and **UK GDPR** (UK).

- Do **not** send this file to external AI tools.
- Downstream code must never print, log, or export `patient_id` values.
- Business rules and expected metrics: `docs/data-contract/CONTEXT-HealthCore.md`.

## 💡 Tips

- Prefer synthetic or de-identified samples in git when possible.
- Document each new file: origin, schema, approximate size, and PII/PHI risk.
- Do not store pipeline outputs here — use `data/process/` for that.

> Spanish version: [README.es.md](./README.es.md).
