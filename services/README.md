# services

This folder contains backend service boundaries for the monorepo architecture.

## Purpose

- Keep backend concerns independent from UI applications.
- Enable future APIs to evolve as separate deployable units.
- Make domain ownership explicit by service area.

## Current architecture placeholders

- `_template-service/` blueprint for creating a new service.
- `gateway/` edge and cross-cutting backend concerns.
- `clinical-operations/` appointments and clinical workflow services.
- `revenue-cycle/` billing and claims services.
- `compliance/` governance and audit services.

## Implemented (Python, reusable by CLI / API)

- `incidents_analysis/` — HealthCore patient incident CSV analysis (`models`, `csv_reader`, `validator`, `analyzer`, `exporter`). Consumed by `scripts/analyze.py` and by the API domain layer.
- `app/` — FastAPI application (`services/app/main.py`) with layered layout:
	- `core/` — TinyDB (`database.py`) and supplier seed (`seed.py`)
	- `models/` — Pydantic supplier models
	- `domain/` — business orchestration (`supplier_service`, `incident_service`)
	- `routers/` — HTTP only:
		- `incidents.py` → `POST /api/incidents/analyze`, `GET /api/incidents/results/export`
		- `suppliers.py` → supplier directory CRUD + filters + rate/status updates

Run from repo root:

```bash
python -m uvicorn services.app.main:app --reload
python -m services.app.core.seed
```

### Runtime data paths used by `services/app`

- `data/process/results.csv` — latest incidents summary export.
- `data/process/suppliers/suppliers.json` — TinyDB runtime file for supplier directory.

## Status

Incident analysis business logic lives under `incidents_analysis/` and is reused by API routes via `app/domain/incident_service`. Other domain folders (`gateway`, `clinical-operations`, `revenue-cycle`, `compliance`) remain placeholders.

> Spanish version: [README.es.md](./README.es.md).
