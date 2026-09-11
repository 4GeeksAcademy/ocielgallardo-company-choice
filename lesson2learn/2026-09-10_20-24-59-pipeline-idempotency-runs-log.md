---
title: Pipeline idempotency and pipeline_runs audit log
category: Procedure
created: 2026-09-10 20:24:59
tags:
  - prefect
  - data-pipelines
  - idempotency
  - healthcore
source: Part 2 Phase 3 Monthly Clinic Supply Performance
status: completed
---

# Pipeline idempotency and pipeline_runs audit log

## Context

Part 2 Phase 3 hardens the Monthly Clinic Supply Performance ETL so a second run over the same month does not duplicate KPI rows, and every attempt leaves an auditable record in Supabase.

## Main Content

### Idempotent load

Destination table `reporting.monthly_clinic_supply_performance` has `UNIQUE (clinic_id, month_start)`.

Load uses:

```sql
INSERT ... ON CONFLICT (clinic_id, month_start) DO UPDATE SET ...
```

Effect: re-running the pipeline for the same month overwrites the same clinic rows. Partial failure mid-load followed by a retry converges to the same result as a clean run (no double counting).

### Execution log — `reporting.pipeline_runs`

Each run inserts a row at start (`status=running`, `phase=extract`) and updates it on success or failure.

Minimum audit fields:

| Field | Purpose |
| --- | --- |
| `run_id` | Unique attempt id |
| `started_at` | Run began (proves the pipeline ran) |
| `finished_at` | Run ended / hang detection |
| `status` | `running` \| `completed` \| `failed` |
| `records_processed` | KPI rows upserted |
| `error_message` | Captured exception text when failed |

Also stored: `phase`, `records_extracted`, `month_start`, `window_start`, `window_end`.

### Helper for Phase 5

`get_latest_pipeline_run()` returns the newest `pipeline_runs` row (JSON-serializable) for `GET /reporting/pipeline-runs/latest`.

## Commands

```bash
PYTHONPATH=. uv run python data/pipelines/pipeline.py
# Run twice: expect two pipeline_runs rows, no duplicate KPI keys
```

## Best Practices

- Rely on the CONTEXT unique constraint for upsert — do not append KPI facts.
- Persist `failed` + `error_message` even when the ETL raises, so silence ≠ success.
- Keep run logging next to the orchestrator in `data/pipelines/`, not in HTTP routers.

## Common Mistakes

- Logging only to stdout — board ops need a queryable table.
- Treating “0 KPI rows” as “pipeline did not run” — check `pipeline_runs` first.

## References

- `data/pipelines/pipeline.py`
- `data/pipelines/reporting_schema.sql`
- `data/pipelines/PIPELINE_DESIGN.md` §6.2
