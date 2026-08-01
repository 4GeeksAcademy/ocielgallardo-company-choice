# 🧠 incidents_analysis

Reusable **patient incident report** analysis for HealthCore — the shared brain behind the CLI today and the API tomorrow.

Package import path: `services.incidents_analysis` (underscore — required by Python).

Priya Nair's team needs a trustworthy summary of clinic incident CSVs. This package owns that logic so `scripts/analyze.py` and a future `POST /api/incidents/analyze` can call the **same** modules.

## Why this service exists

```text
CLI path                         Future API path
--------                         ---------------
analyze.py                       POST /api/incidents/analyze
     |                                    |
     +----------->  this package  <-------+
                  (one source of truth)
```

No business rules in the script. No duplicated validators in the router. One place to change when CONTEXT rules evolve.

## 🗂 Module map

| Module | Responsibility |
| --- | --- |
| `models.py` | Shared data shapes (`Incident`) — dataclass |
| `csv_reader.py` | Open and read the UTF-8 comma-separated CSV (header required) |
| `validator.py` | Apply CONTEXT invalidity rules; count by rule; never expose `patient_id` |
| `analyzer.py` | Aggregate metrics from **valid** records (and invalid breakdown from invalid ones) |
| `exporter.py` | Write metrics CSV (`metric`, `value`, optional `percentage`) — no PHI |
| `__init__.py` | Package marker / public exports |

## 🔄 Flow (high level)

1. Read CSV from disk (sample lives in `data/raw/incidents-healthcore.csv`).
2. Validate each record against CONTEXT rules.
3. Compute totals, category/status/(optional country) breakdowns, satisfaction index.
4. Callers present results (console today; JSON later) and may export metrics.

Design detail: `docs/data-contract/functional-design-analyze.md`  
Business contract: `docs/data-contract/CONTEXT-HealthCore.md`

## 🔒 Compliance

`patient_id` is PHI / personal data. This package must:

- never print, log, or export raw `patient_id` values — including in error messages;
- report only rule names and counts when identifiers are missing/invalid;
- treat zero patient exposure as a hard requirement, not a preference.

## How to run (CLI)

From the repo root:

```bash
python scripts/analyze.py data/raw/incidents-healthcore.csv
```

Expected against the official sample: **100** rows, **94** valid, **6** invalid; satisfaction average **3.58**. Optional export writes `data/process/results.csv`.

## Status

**CLI pipeline implemented** (Paso 3 closed): `models` → `csv_reader` → `validator` → `analyzer` → `exporter`, orchestrated by `scripts/analyze.py`.

Next project milestone: FastAPI (and UI) reusing these same modules — not started here.

> Spanish twin of the contract: [CONTEXT-HealthCore.es.md](../../docs/data-contract/CONTEXT-HealthCore.es.md).
