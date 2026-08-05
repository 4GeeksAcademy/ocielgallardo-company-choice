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

## Implemented (Python, reusable by CLI / future API)

- `incidents_analysis/` — HealthCore patient incident CSV analysis (`models`, `csv_reader`, `validator`, `analyzer`, `exporter`). Consumed by `scripts/analyze.py`.
- `api/` — centralized FastAPI entrypoint (`services/api/main.py`) with domain routers:
	- `routers/incidents.py` → `POST /api/incidents/analyze`, `GET /api/incidents/results/export`
	- `routers/suppliers.py` → supplier directory CRUD + filters + rate/status updates

### Runtime data paths used by `services/api`

- `data/process/results.csv` — latest incidents summary export.
- `data/process/suppliers/suppliers.json` — TinyDB runtime file for supplier directory.

## Status

Incident analysis business logic lives under `incidents_analysis/` and is reused by API routes. Other domain folders (`gateway`, `clinical-operations`, `revenue-cycle`, `compliance`) remain placeholders.

> Spanish version: [README.es.md](./README.es.md).
