---
title: Backend incident analysis — from CLI pipeline to FastAPI
category: Learning
created: 2026-08-01T13:17:48
tags:
  - python
  - fastapi
  - csv
  - healthcore
  - incidents
  - architecture
source: bitacora.md (2026-07-31 Pasos 1–3; 2026-08-01 Fase 2 backend)
status: completed
---

# Backend incident analysis — from CLI pipeline to FastAPI

## Context

HealthCore patient-incident CSV analysis (CONTEXT in `docs/data-contract/`). Backend work split into:

- **Phase 1 (Pasos 1–3, 2026-07-31):** design the flow, define reusable modules, implement CLI end-to-end.
- **Phase 2 backend (2026-08-01):** expose the **same** modules via FastAPI (`POST /api/incidents/analyze`, `GET /api/incidents/results/export`).

Goal of this note: what to internalize to rebuild this style of backend.

## Main Content

### Core idea

Put business rules in one package. Thin entrypoints (CLI script or HTTP router) only orchestrate.

```text
CSV → read → validate → analyze → (export metrics)
              ↑
   services/incidents_analysis/
```

CLI (`scripts/analyze.py`) and API (`services/api/routers/incidents.py`) both call that package. Do not copy validators into the router.

### Phase 1 — build the brain first

1. **Functional design before code** — document read → validate → metrics → console → optional CSV export (`docs/data-contract/functional-design-analyze*.md`). Mark CONTEXT ambiguities with TODOs; do not invent rules.
2. **Folder layout for reuse** — orchestration in `scripts/`; domain logic in `services/incidents_analysis/` (`models`, `csv_reader`, `validator`, `analyzer`, `exporter`).
3. **Importable package name** — use `incidents_analysis` (underscore). Hyphenated folder names are not valid Python imports.
4. **Implement dependency order** — `models` → `csv_reader` → `validator` → `analyzer` → `exporter` → thin `analyze.py`.
5. **`dataclass` for `Incident`** — shape only (9 CONTEXT fields; `satisfaction_score: int | None`). No I/O and no business rules in `models.py`.
6. **Reader stays dumb** — UTF-8, comma, header via `csv.DictReader`; empty score → `None`; never print `patient_id`.
7. **Validator owns CONTEXT rules** — first failing rule per row; count by rule key; never expose `patient_id` in messages.
8. **Analyzer aggregates only valid rows** (+ invalid breakdown counts). Categories/statuses/countries must match CONTEXT names exactly.
9. **Exporter writes metrics CSV** — columns `metric`, `value`, `percentage`; overwrite mode (`"w"`); no PHI. Default path: `data/process/results.csv`.
10. **CLI is a coordinator** — adds repo root to `sys.path`, calls modules, prints report, prompts export.

Official sample expectation: **100** rows, **94** valid, **6** invalid, satisfaction average **3.58**.

### Phase 2 backend — expose the brain over HTTP

1. **`main.py` vs routers** — `services/api/main.py` creates `FastAPI`, CORS, `include_router`. Endpoints live in `services/api/routers/incidents.py`.
2. **Keep `__init__.py`** — marks `services/api` and `routers` as packages so `uvicorn services.api.main:app` imports cleanly.
3. **`POST /api/incidents/analyze`** — `multipart/form-data`, field name `file`, `UploadFile` + `File(...)`. Needs `python-multipart`. Reject non-`.csv` with HTTP **400**.
4. **Bridge upload → disk reader** — `read_incidents` expects a path: write bytes to a temp file, analyze, delete temp in `finally`.
5. **Persist last run for export** — inside the `try`, after `summary = analyze_incidents(...)`, call `export_results(summary, RESULTS_CSV)` **before** `return summary`. Code after `return` never runs.
6. **POST returns JSON; GET returns file** — POST → summary dict. `GET /api/incidents/results/export` → `FileResponse` of last CSV, or **404** if missing.
7. **CORS** — browser UI on another origin/port needs `CORSMiddleware`. Allow every local UI port you actually use (e.g. `3000` and `3001` when Next picks an alternate port).
8. **Run from repo root** — `python -m uvicorn services.api.main:app --reload` (prefer `python -m uvicorn` over bare `uvicorn` on Windows).

### Compliance (always)

`patient_id` is PHI. Never log, print, JSON-return, or export raw patient IDs. Report only rule names and counts.

## Steps

1. Read CONTEXT + write functional design (no code).
2. Create `services/incidents_analysis/` package + thin `scripts/analyze.py` stub.
3. Implement modules in dependency order; validate with the official CSV after each layer that can be tested.
4. Add FastAPI app: `main` + `routers/incidents`.
5. Wire POST analyze to the same pipeline; save last results CSV.
6. Add GET export with `FileResponse` + 404 when empty.
7. Enable CORS for the frontend origin(s); smoke-test with `curl` then the UI.

## Commands

```bash
# Phase 1 — CLI
python scripts/analyze.py data/raw/incidents-healthcore.csv

# Phase 2 — API deps (if not installed)
python -m pip install fastapi uvicorn python-multipart

# Phase 2 — start API from repo root
python -m uvicorn services.api.main:app --reload

# Smoke tests
curl -X POST "http://127.0.0.1:8000/api/incidents/analyze" \
  -F "file=@data/raw/incidents-healthcore.csv"

curl -OJ "http://127.0.0.1:8000/api/incidents/results/export"
```

## Examples

Package layout (Phase 1):

```text
scripts/analyze.py
services/incidents_analysis/
  models.py
  csv_reader.py
  validator.py
  analyzer.py
  exporter.py
data/raw/incidents-healthcore.csv
data/process/results.csv          # generated; often gitignored
```

API layout (Phase 2):

```text
services/api/
  main.py                 # FastAPI + CORS + include_router
  routers/incidents.py    # POST /analyze, GET /results/export
```

POST orchestration pattern:

```python
summary = analyze_incidents(valid, invalid_counts, total=len(incidents))
export_results(summary, RESULTS_CSV)  # persist last run
return summary                        # JSON to client
```

## Common Mistakes

- Putting business rules inside the FastAPI router or CLI instead of `incidents_analysis`.
- Naming the package `incidents-analysis` (not importable).
- Calling `export_results` after `return summary` (dead code).
- Returning the CSV from POST; export belongs on GET.
- Forcing `Content-Type: application/json` on multipart uploads (breaks file upload).
- Allowing only `localhost:3000` in CORS while the UI runs on `3001`.
- Printing or exporting `patient_id`.
- Inventing category/status/rule names that do not match CONTEXT.

## Best Practices

- Design → structure → implement module by module.
- One source of truth for validation and metrics.
- Thin HTTP/CLI layers; fat domain package.
- Exact CONTEXT vocabularies in APIs and exports.
- Treat regenerable outputs (`results.csv`, `__pycache__`) as non-source artifacts.
- Prefer `python -m uvicorn` for reliable local runs.

## References

- `docs/data-contract/CONTEXT-HealthCore.md` / `.es.md`
- `docs/data-contract/functional-design-analyze.md` / `.es.md`
- `services/incidents_analysis/`
- `scripts/analyze.py`
- `services/api/main.py`
- `services/api/routers/incidents.py`
- `bitacora.md` — entries 2026-07-31 (Pasos 1–3) and 2026-08-01 (Fase 2)
