# 🚀 `scripts` — thin entrypoints and team tooling

This folder holds **CLI entrypoints** and helper scripts for the monorepo: analysis runners, setup helpers, and other support tools that should stay easy to invoke from the repo root.

Rule of thumb: scripts **orchestrate**; reusable logic lives elsewhere (for example under `services/`).

## Purpose

- Give humans a simple command to run without digging into package internals.
- Keep business rules out of one-off script files so the same logic can power a future API.
- Document how to run each script safely (especially when PHI/PII is involved).

## 📁 Scripts in this folder

### `analyze.py` — patient incident report analysis (CLI)

Coordinates the end-to-end flow for HealthCore incident CSV analysis. It does **not** own business rules; it calls into `services/incidents_analysis`.

```text
analyze.py
    |
    +-- csv_reader   -> read the CSV
    +-- validator    -> valid / invalid rules
    +-- analyzer     -> aggregate metrics
    +-- console      -> print the report
    +-- exporter     -> optional metrics CSV (after y/n prompt)
```

**Typical usage** (from repo root; path may vary by environment):

```bash
python scripts/analyze.py data/raw/incidents-healthcore.csv
```

**Source of truth**

- Requirements: `docs/data-contract/CONTEXT-HealthCore.md`
- Functional flow: `docs/data-contract/functional-design-analyze.md`
- Reusable modules: `services/incidents_analysis/`
- Export (optional): `data/process/results.csv`

🛡 **Compliance reminder:** never print or export `patient_id`. If the script surfaces a patient identifier, the output is not usable.

### `seed_incidents.py` — load historical customer incidents into TinyDB

Validates `data/raw/incidents-healthcore.csv` with shared analyzer rules (`packages/shared/healthcore_shared`), maps rows to the incident-manager model (CONTEXT transforms), and inserts idempotently by `source_incident_id`.

```bash
# from repo root
PYTHONPATH=packages/shared uv run python scripts/seed_incidents.py
# or
uv run seed-incidents
```

**Source of truth:** `docs/incident-manager/CONTEXT-HealthCore.md`

### `extract-lighthouse-kpis.mjs` — KPI table from Lighthouse HTML exports

Parses `window.__LIGHTHOUSE_JSON__` from saved Lighthouse HTML reports and prints Performance, FCP, LCP, INP (or maxPotentialFID lab proxy), CLS, TTFB, and TBT.

```bash
node scripts/extract-lighthouse-kpis.mjs audit/before/*.html --markdown
node scripts/extract-lighthouse-kpis.mjs audit/after/*.html --markdown
node scripts/extract-lighthouse-kpis.mjs audit/final/*.html --markdown
```

Use after each audit pass to fill [`AUDIT.md`](../audit/AUDIT.md) and [`REPORT.md`](../audit/REPORT.md) tables.

### `seed_inventory_volume.py` — append inventory volume for caching benchmarks

Adds ~200 extra `medical_supplies` rows plus thousands of `supply_deliveries` and `supply_consumptions` in Supabase for realistic read latency. Idempotent: skips when `supply_deliveries` already has ≥1000 rows. Does **not** replace the CONTEXT seed in `services/app/core/inventory_seed.py`.

```bash
# from repo root (requires SUPABASE_DB_* or DATABASE_URL in .env)
uv run python scripts/seed_inventory_volume.py
# or
uv run seed-inventory-volume
```

### `measure_cache_candidates.py` — row counts and latency for cache shortlist

Runs 10 iterations (default) and reports min / p50 / max latency for inventory, incidents summary, and suppliers. Domain mode hits service functions directly; `--http` mode requires a running API and `BENCHMARK_USERNAME` / `BENCHMARK_PASSWORD` in `.env`.

```bash
uv run python scripts/measure_cache_candidates.py
uv run python scripts/measure_cache_candidates.py --json
uv run python scripts/measure_cache_candidates.py --http --base-url http://127.0.0.1:8000
```

Use before and after `seed_inventory_volume.py` to fill [`CACHING_REPORT.md`](../CACHING_REPORT.md) Phase 2 tables.

## 💡 Tips

- Keep each script focused: parse args, call services, present results.
- Prefer importing from `services/` over copying logic into the script.
- Document parameters, expected inputs, and side effects (files written, interactive prompts).

> Spanish version: [README.es.md](./README.es.md).
