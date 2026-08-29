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

- `incidents_analysis/` — HealthCore patient incident CSV analysis (`models`, `csv_reader`, `validator` re-exports `healthcore_shared`, `analyzer`, `exporter`). Consumed by `scripts/analyze.py` and by the API domain layer.
- `app/` — FastAPI application (`services/app/main.py`) with layered layout:
  - `core/` — TinyDB + SQLModel engine (`database.py`), seeds, JWT/password helpers (`security.py`), `deps.py` (`get_current_user`)
  - `models/` — Pydantic (`supplier`, `user`, `profile`) and SQLModel inventory ORM (`inventory.py`)
  - `schemas.py` — Pydantic request/response for inventory (separate from ORM)
  - `domain/` — business orchestration (`supplier_service`, `incident_service`, `user_service`, `profile_service`, `inventory_service`)
  - `routers/` — HTTP only:
    - `incidents.py` → CSV analyze/export **and** manager CRUD:
      - `POST /api/incidents/analyze`, `GET /api/incidents/results/export` (public)
      - `POST /api/incidents`, `GET /api/incidents`, `GET /api/incidents/summary`, `GET /api/incidents/{id}`, `PATCH /api/incidents/{id}/status` (**Bearer required**)
		- `suppliers.py` → supplier directory CRUD + filters + rate/status updates (**Bearer required**)
		- `users.py` → user credential CRUD (`POST` public; `GET/PUT/DELETE` require Bearer; PUT/DELETE self-or-admin)
		- `auth.py` → `POST /auth/login`, `GET /auth/me`, `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/change-password`
		- `profiles.py` → `GET/PUT /profiles/me` (JWT)
		- `inventory.py` → `/inventory/*` medical supplies + deliveries/consumptions (**Bearer required**)

Shared validation/constants: `packages/shared/healthcore_shared` (see `packages/shared/README.md`). Seed historical incidents: `PYTHONPATH=packages/shared uv run python scripts/seed_incidents.py`.

Auth notes (AUTH-01 / AUTH-03):

- Passwords hashed with `passlib` + `bcrypt` (pin `bcrypt==4.0.1` for passlib compatibility).
- JWT signed with `python-jose`; `SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_MINUTES` from repo-root `.env` (see `.env.example`).
- User and Profile stored only in TinyDB (not PostgreSQL/Supabase). Password-reset tokens live in TinyDB table `password_reset_tokens` (hashed, short TTL, single-use).
- All `/suppliers` routes and non-public `/users` routes require `Authorization: Bearer <token>` (401 without it).
- Serialization (milestone complete on `feature/serialization-audit`): every JSON endpoint declares an explicit Pydantic `response_model`. Register returns `RegisterResponse` (no email). Login returns token only. `GET /auth/me` may return caller email. Checklist: [`docs/audit/serialization-audit.md`](../docs/audit/serialization-audit.md).
- Password recovery (AUTH-03, branch `feature/password-reset`):
  - `POST /auth/forgot-password` always returns 200 (anti-enumeration); emails via Resend when the user exists.
  - `POST /auth/reset-password` validates token/expiry/single-use; updates hash; invalidates token.
  - `POST /auth/change-password` requires Bearer; verifies current password first.
  - Env: `RESEND_API_KEY`, `EMAIL_FROM` (use `onboarding@resend.dev` for Resend onboarding), `FRONTEND_BASE_URL`, `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`, optional `EMAIL_SSL_VERIFY` (local Windows TLS workaround). Never commit real keys.
- Frontend consumer (AUTH-02/03): backoffice stores the JWT in `localStorage` and sends Bearer via `uis/backoffice/lib/services/healthcoreClient.ts` (`/login`, `/register`, forgot/reset/change-password flows).

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
PYTHONPATH=packages/shared uv run python -m uvicorn services.app.main:app --reload
uv run python -m services.app.core.seed
uv run python -m services.app.core.inventory_seed
PYTHONPATH=packages/shared uv run python scripts/seed_incidents.py
```

### Runtime data paths used by `services/app`

- `data/process/results.csv` — latest incidents analysis metrics export.
- `data/process/suppliers/suppliers.json` — TinyDB runtime file for supplier directory.
- `data/process/auth/auth.json` — TinyDB runtime file for users, profiles, and password-reset tokens (gitignored).
- `data/process/incidents/incidents.json` — TinyDB runtime file for the centralized incident manager (gitignored).

## Status

Incident analysis business logic lives under `incidents_analysis/` and is reused by API routes via `app/domain/incident_service`. AUTH-01 JWT protection is applied to users (except register) and all supplier routes; inventory routes require Bearer. Incidents remain public for now. Other domain folders (`gateway`, `clinical-operations`, `revenue-cycle`, `compliance`) remain placeholders.
Incident CSV analysis lives under `incidents_analysis/` (validator rules shared via `healthcore_shared`) and is reused by `app/domain/incident_service`. The **incident manager** persists rows in TinyDB and exposes authenticated CRUD/summary/status endpoints (`incident_manager_service`). AUTH-01 JWT protection applies to users (except register), suppliers, and manager incident routes; CSV analyze/export remain public. AUTH-03 adds forgot/reset/change-password with Resend. Backoffice AUTH-02/03 attach Bearer from `localStorage` after `/login` or `/register` and expose password recovery UI. Other domain folders (`gateway`, `clinical-operations`, `revenue-cycle`, `compliance`) remain placeholders.

> Spanish version: [README.es.md](./README.es.md).
