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
  - `core/` — TinyDB + SQLModel engine (`database.py`), seeds, JWT/password helpers (`security.py`), `deps.py` (`get_current_user`)
  - `models/` — Pydantic (`supplier`, `user`, `profile`) and SQLModel inventory ORM (`inventory.py`)
  - `schemas.py` — Pydantic request/response for inventory (separate from ORM)
  - `domain/` — business orchestration (`supplier_service`, `incident_service`, `user_service`, `profile_service`, `inventory_service`)
  - `routers/` — HTTP only:
    - `incidents.py` → `POST /api/incidents/analyze`, `GET /api/incidents/results/export`
		- `suppliers.py` → supplier directory CRUD + filters + rate/status updates (**Bearer required**)
		- `users.py` → user credential CRUD (`POST` public; `GET/PUT/DELETE` require Bearer; PUT/DELETE self-or-admin)
		- `auth.py` → `POST /auth/login`, `GET /auth/me` (JWT)
		- `profiles.py` → `GET/PUT /profiles/me` (JWT)
		- `inventory.py` → `/inventory/*` medical supplies + deliveries/consumptions (**Bearer required**)

Auth notes (AUTH-01, branch `feature/auth`):

- Passwords hashed with `passlib` + `bcrypt` (pin `bcrypt==4.0.1` for passlib compatibility).
- JWT signed with `python-jose`; `SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_MINUTES` from repo-root `.env` (see `.env.example`).
- User and Profile stored only in TinyDB (not PostgreSQL/Supabase).
- All `/suppliers` routes and non-public `/users` routes require `Authorization: Bearer <token>` (401 without it).

Inventory notes (Hito 5, branch `feature/inventory`):

- Dual DB: TinyDB (auth/users) + Supabase PostgreSQL via SQLModel.
- Supabase connection (repo-root `.env`, see `.env.example`):
  - Preferred: discrete vars `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, `SUPABASE_DB_NAME`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD` (Transaction / Shared pooler).
  - Optional override: full `DATABASE_URL` (password must be percent-encoded if it contains special characters).
  - `services/app/core/database.py` builds the URI with `quote_plus` when using discrete vars; never commit secrets to git.
- Entities: `MedicalSupply`, `SupplyDelivery`, `SupplyConsumption`. Stock is computed, never stored.
- Context: `docs/inventory/CONTEXT-HealthCore.es.md`

Run from repo root:

```bash
uv run python -m uvicorn services.app.main:app --reload
uv run python -m services.app.core.seed
uv run python -m services.app.core.inventory_seed
```

### Runtime data paths used by `services/app`

- `data/process/results.csv` — latest incidents summary export.
- `data/process/suppliers/suppliers.json` — TinyDB runtime file for supplier directory.
- `data/process/auth/auth.json` — TinyDB runtime file for users and profiles (gitignored).

## Status

Incident analysis business logic lives under `incidents_analysis/` and is reused by API routes via `app/domain/incident_service`. AUTH-01 JWT protection is applied to users (except register) and all supplier routes; inventory routes require Bearer. Incidents remain public for now. Other domain folders (`gateway`, `clinical-operations`, `revenue-cycle`, `compliance`) remain placeholders.

> Spanish version: [README.es.md](./README.es.md).
