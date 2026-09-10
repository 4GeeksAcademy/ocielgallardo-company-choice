---
title: Reporting API endpoints for monthly clinic KPIs
category: Procedure
created: 2026-09-11 01:24:00
tags:
  - fastapi
  - data-pipelines
  - reporting
  - healthcore
source: Part 2 Phases 4–5 Monthly Clinic Supply Performance
status: completed
---

# Reporting API endpoints for monthly clinic KPIs

## Context

Part 2 closes with Phase 4 (CLI/cadence docs) and Phase 5 (`services/reporting/` API). Business KPIs leave the CLI and become authenticated HTTP for backoffice / leadership.

## Main Content

### Module layout

| Path | Role |
| --- | --- |
| `services/reporting/router.py` | FastAPI `APIRouter(prefix="/reporting")` |
| `services/reporting/schemas.py` | Pydantic response models |
| `data/pipelines/pipeline.py` | `get_latest_pipeline_run`, `query_…`, `trigger_…` |

No ETL inside the router — only imports from `data/pipelines/`.

### Endpoints

| Method | Path | Helper |
| --- | --- | --- |
| GET | `/reporting/pipeline-runs/latest` | `get_latest_pipeline_run` |
| POST | `/reporting/pipeline-runs` | `trigger_monthly_clinic_supply_performance_run` → `run_monthly…` (`.fn()` path) |
| GET | `/reporting/monthly-clinic-supply-performance` | `query_monthly_clinic_supply_performance` |

All use `Depends(get_current_user)` (Bearer), same pattern as inventory.

### Why reporting is auth’d and telemetry is not

- **Reporting** exposes clinic-level cost/stockout KPIs and can start a DB-writing ETL.
- **Telemetry** (`POST /telemetry/events`, `GET /telemetry/report`) stays open so browser capture (`track` / `sendBeacon`) works without a session — including auth-failure events. CONTEXT forbids changing that path in this milestone.

### Validation

OpenAPI tag `reporting` on `/docs`. Without token → 401; with Bearer → 200 (or 404 if no runs yet).

## Key Takeaways

1. Keep HTTP thin: services call pipeline helpers; pipelines own SQL/ETL.
2. Protect write triggers and business aggregates with the same JWT gate as inventory.
3. Do not unify telemetry auth with reporting unless a later security milestone explicitly scopes it.
