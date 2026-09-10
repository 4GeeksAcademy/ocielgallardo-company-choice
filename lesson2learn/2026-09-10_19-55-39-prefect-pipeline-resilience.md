---
title: Prefect pipeline resilience — retries, cache, return_state
category: Procedure
created: 2026-09-10 19:55:39
tags:
  - prefect
  - data-pipelines
  - healthcore
  - resilience
source: Part 2 Phase 1–2 Monthly Clinic Supply Performance
status: completed
---

# Prefect pipeline resilience — retries, cache, return_state

## Context

HealthCore Part 2 builds a business KPI pipeline (`monthly_clinic_supply_performance_flow`) that reads `telemetry_events` and upserts into `reporting.monthly_clinic_supply_performance`. Phase 1 wired extract → transform → load plus an optional eval snapshot. Phase 2 made that ETL resilient for unattended runs.

## Main Content

### Phase 1 structure

| Piece | Role |
| --- | --- |
| `@flow` `monthly_clinic_supply_performance_flow` | Orchestrates the ETL |
| `extract_supply_telemetry` | Read-only SELECT from `telemetry_events` for one UTC month |
| `transform_monthly_clinic_kpis` | Dedupe by `event_id`, aggregate four CONTEXT KPIs |
| `load_monthly_clinic_supply_performance` | Upsert on `(clinic_id, month_start)` |
| `write_eval_snapshot` | Optional JSON under `data/eval/` — not the board table |

Pure aggregation lives in `data/process/reporting/monthly_clinic_kpis.py`. DDL is `data/pipelines/reporting_schema.sql`.

### Phase 2 resilience

1. **Retries on external I/O** — `extract_*` and `load_*` use `retries=3` and `retry_delay_seconds=10` to absorb transient Supabase/network failures without long stalls.
2. **Transform cache** — `cache_key_fn=task_input_hash` (hash of events + `month_start`) and `cache_expiration=timedelta(hours=1)` so a re-run within one hour with the same inputs skips recomputation.
3. **Explicit failure handling** — in the flow, `load_…(return_state=True)` aborts if load did not complete; `write_eval_snapshot(…, return_state=True)` logs a warning and lets the flow succeed if KPIs already loaded.

### CLI note (Windows paths with spaces)

Prefect’s ephemeral API server can fail when the repo path contains spaces (Alembic cannot load migration files). Without `PREFECT_API_URL`, the CLI uses `task.fn()` via `run_monthly_clinic_supply_performance()` so the ETL still runs. Set `PREFECT_API_URL` to use the full Prefect flow engine.

## Commands

```bash
# From repo root
PYTHONPATH=. uv run python data/pipelines/pipeline.py

# Dependency
uv add "prefect>=3"
```

## Best Practices

- Put retries only on tasks that talk to external services (DB/API), and justify the count in a comment.
- Cache expensive pure transforms; key must include all inputs that change the result.
- Use `return_state=True` for non-critical side effects so a snapshot/notify failure does not undo a successful load.
- Keep ETL in `data/pipelines/`; HTTP endpoints (later) only import the flow — never duplicate logic in `services/`.

## Common Mistakes

- Treating the eval snapshot as the board deliverable — the destination table is `reporting.monthly_clinic_supply_performance`.
- Calling optional tasks without `return_state=True` so a disk error fails the whole monthly pack.
- Expecting the ephemeral Prefect server to work on every Windows path; use `PREFECT_API_URL` or the `.fn()` CLI path.

## References

- `data/pipelines/pipeline.py`
- `data/pipelines/PIPELINE_DESIGN.md` §6.1
- `docs/data-pipelines/CONTEXT-healthcore-phase-2.md`
