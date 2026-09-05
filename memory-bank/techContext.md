# Technical Context

## Stack Summary
- Frontend apps: Next.js + React for public and internal UIs.
- Domain and utilities: TypeScript (typed models and utility modules).
- Package tooling: npm scripts via `packages/shared/package.json`.
- Shared Python package: `packages/shared/healthcore_shared` (CSV validation + incident-manager constants/maps). Import via `PYTHONPATH=packages/shared` or hatch `dev-mode-dirs`.
- Local Docker Compose (`#infra-40`): `uis` (website `:3000` + backoffice `:3001`) and `backend` (`:8000`) on `healthcore_dev_network`. Start from repo root: `docker compose up`. Browser API URL: `NEXT_PUBLIC_HEALTHCORE_API_URL=http://localhost:8000`; in-network hostname: `backend`.

## Verified Technical Areas
- TypeScript domain package in `src/`:
  - `types/models.ts`
  - `utils/collections.ts`
  - `utils/search.ts`
  - `utils/transformations.ts`
  - `utils/validations.ts`
- Type test file: `src/types/models.type-test.ts`.
- UI applications:
  - `uis/website` (public Next.js website)
  - `uis/backoffice` (internal Next.js workspace)
- Telemetry capture + storage:
  - `uis/backoffice/lib/services/telemetry.ts` — queue, batch, sendBeacon, retry, `track()`
  - `uis/backoffice/components/WebVitalsReporter.tsx` — Core Web Vitals via PerformanceObserver
  - Backend ingest: `services/app/routers/telemetry.py` — `POST /telemetry/events` (per-event Pydantic validate + bulk insert)
  - Domain: `services/app/domain/telemetry_service.py` — allowlist `tags` from `docs/telemetry/event-schemas.json`
  - Table: `telemetry_events` (SQLModel `services/app/models/telemetry.py`; DDL `docs/telemetry/telemetry-events.sql`)
- Backoffice auth client (AUTH-02 complete):
  - Token key `healthcore_access_token` in `localStorage` via `uis/backoffice/lib/services/healthcoreClient.ts`
  - Pages `/login`, `/register`, `/account/profile`; successful auth redirects to `/`
  - Bearer on HealthCore API calls; 401 clears session and redirects to `/login`
  - `AppChrome` guards routes; `BackofficeShell` exposes Profile nav + logout (`clearSessionAndRedirectToLogin`)
- Password reset / change (AUTH-03 complete on `feature/password-reset`):
  - Public pages `/forgot-password`, `/reset-password`; authenticated `/account/change-password`
  - API: `POST /auth/forgot-password`, `/auth/reset-password`, `/auth/change-password`
  - Reset tokens in TinyDB `password_reset_tokens` (hashed, short TTL, single-use)
  - Email via Resend (`RESEND_API_KEY`, `EMAIL_FROM=onboarding@resend.dev`, `FRONTEND_BASE_URL`; optional `EMAIL_SSL_VERIFY` for local TLS)
  - Dependency: `certifi` for HTTPS CA bundle when SSL verify is enabled
- Internal Hito 2 demo surface:
  - `uis/backoffice/components/dashboard/Hito2Playground.tsx`
- Inventory backoffice UI (Hito 5, `feature/inventory`, not merged):
  - `/inventory/products`, `/inventory/orders/inbound`, `/inventory/orders/outbound`, `/inventory/orders`
  - Client `uis/backoffice/lib/services/inventoryApi.ts`; types `uis/backoffice/types/inventory.ts`
- Service architecture placeholders:
  - `services/gateway`
  - `services/clinical-operations`
  - `services/revenue-cycle`
  - `services/compliance`
- Implemented backend FastAPI app:
  - `services/app/` (`main`, `core`, `models`, `schemas`, `domain`, `routers`)
  - `services/incidents_analysis/` (CLI/API shared incident CSV pipeline)
  - Auth: JWT via `python-jose`, passwords via `passlib`/`bcrypt`, TinyDB users/profiles, config from root `.env`
  - Inventory (Hito 5): SQLModel + Supabase PostgreSQL via `SUPABASE_DB_*` (or optional `DATABASE_URL`); TinyDB remains for auth only
  - Entities: `MedicalSupply`, `SupplyDelivery`, `SupplyConsumption` under `/inventory`
  - Serialization audit (**complete**): explicit `response_model` on all JSON routes; checklist `docs/audit/serialization-audit.md`
  - Run: `PYTHONPATH=packages/shared uv run python -m uvicorn services.app.main:app --reload`
  - Incident manager: TinyDB `data/process/incidents/incidents.json`; CRUD + `/api/incidents/summary` + status lifecycle; seed via `scripts/seed_incidents.py`

## Validation and Local Checks
- Type validation command (documented):
  - `cd /workspaces/ocielgallardo-company-choice/packages/shared`
  - `npm run test:types:models`

## Repository Navigation Guide
- `CONTEXT.md`: business domain baseline and company scenario.
- `docs/telemetry/`: Telemetry Plan design docs (`telemetry-plan.md`, `event-schemas.json`); CONTEXT metrics in `CONTEXT-healthcore.md`.
- `memory-bank/`: persistent AI-agent context and progress tracking.
- `.agents/rules/`: behavior and contribution constraints for AI agents.
- `docs/`: cross-cutting docs; milestone CONTEXTs and `docs/audit/` (Lighthouse evidence + `CACHING_REPORT.md`).
- `src/`: core typed models and utility logic.
- `uis/`: UI applications and interface-focused projects.
- `services/`: backend/API and workers (future or partial, depending on milestone).
- `data/`: data pipelines and evaluation-oriented assets.
- `skills/` and `agents/`: reusable AI workflows and templates.

## Folder Structure (High-Level)
- Monorepo-like educational structure with top-level domains for UI, services, workflows, data, and shared resources.
- Current implemented business logic remains concentrated in root `src/`.
- Public and internal UIs are now separated into independent apps under `uis/website` and `uis/backoffice`.
- Legacy root HTML/JS surfaces were retired after the monorepo migration.

## Coding Conventions (Observed + Enforced Direction)
- Keep business logic aligned to `CONTEXT.md` definitions.
- Prefer explicit naming over implicit behavior.
- Keep utility functions single-responsibility and composable.
- Use typed interfaces/models for domain entities.
- Add validation rules before processing records where relevant.
- Avoid embedding undocumented business assumptions in code.

## Documentation Conventions for Agents
- Write in concise professional English.
- Mark unknown facts with `TODO:`.
- Keep governance rules in `.agents/rules/` with one responsibility per file.
- Update `memory-bank/progress.md` after meaningful repository changes.

## TODO Gaps
- TODO: Formalize branching strategy and release policy if this evolves beyond milestone delivery.
- TODO: Document canonical lint/test commands across all subprojects if/when standardized.
- TODO: Document data classification levels for PHI/PII handling in implementation docs.
- TODO: Define shared package strategy for cross-UI components if duplication appears.
