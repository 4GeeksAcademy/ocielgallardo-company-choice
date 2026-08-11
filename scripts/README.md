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

## 💡 Tips

- Keep each script focused: parse args, call services, present results.
- Prefer importing from `services/` over copying logic into the script.
- Document parameters, expected inputs, and side effects (files written, interactive prompts).

> Spanish version: [README.es.md](./README.es.md).
