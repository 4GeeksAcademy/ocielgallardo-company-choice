# Progress

## Current Status Snapshot
- Business context source established in `CONTEXT.md`.
- Web deliverables for Milestone 1 are implemented.
- Core TypeScript domain/utilities for Milestone 2 are implemented.
- Manual browser playground for utility inspection is available.
- Type-level model validation command is available in `packages/shared`.
- AUTH-01 (JWT auth) is complete on branch `feature/auth` (route protection + 403 ownership rules applied).
- Hito 5 inventory API (SQLModel + Supabase) and backoffice UI are implemented on branch `feature/inventory` (not merged).

## Recently Completed (Hito 5 — inventory backoffice UI)
- Branch: `feature/inventory` (no merge).
- Four authenticated views: `/inventory/products`, `/inventory/orders/inbound`, `/inventory/orders/outbound`, `/inventory/orders`.
- Client: `uis/backoffice/lib/services/inventoryApi.ts` (Bearer via `healthcoreClient`; no direct `fetch` in components).
- Outbound form shows selected supply `current_stock` reactively, warns when quantity exceeds stock, and surfaces API `400` inline on quantity.
- Order history is read-only with inbound/outbound visual distinction, product name, quantity, date, and `user_uuid`.
- Nav: Suministros, Registrar entrega, Registrar consumo, Historial de órdenes.
- Validation: lints clean on new files. `npx tsc --noEmit` not run here (Node/npm not on PATH; `uis/backoffice/node_modules` absent). Manual API smoke not run in this session.

## Recently Completed (Hito 5 — inventory ORM + dual database)
- Branch: `feature/inventory` (cut from `feature/auth`).
- Context: `docs/inventory/CONTEXT-HealthCore.es.md` (MedicalSupply / SupplyDelivery / SupplyConsumption).
- Dependencies: `sqlmodel`, `psycopg2-binary`.
- Env: `SUPABASE_DB_*` in `.env` (see `.env.example`); optional full `DATABASE_URL` override. Password only in gitignored `.env`.
- Dual DB in `services/app/core/database.py`: TinyDB (auth) + SQLModel engine/`get_db` (inventory); URI built with `quote_plus` from discrete vars.
- ORM: `services/app/models/inventory.py`; Pydantic schemas: `services/app/schemas.py`.
- Domain: `services/app/domain/inventory_service.py` — computed `current_stock`, outbound rejects negative stock with HTTP 400.
- Router: `services/app/routers/inventory.py` under `/inventory` (all routes Bearer-authenticated).
- Seed: `services/app/core/inventory_seed.py` (idempotent); tables + seed also applied on Supabase project `GallaGit's Project`.
- Expected net stocks after seed: HCR-PPE-001=55, HCR-PPE-002=25, HCR-DIAG-001=42, HCR-DIAG-002=15, HCR-WND-001=20, HCR-MED-001=18.
- Local smoke test (SQLite in-memory) verified stock calc + outbound 400. Live Supabase connection verified via `SUPABASE_DB_*` in `.env`.

## Recently Completed (AUTH-01 — authentication foundation)
- Branch: `feature/auth`.
- Dependencies: `passlib[bcrypt]`, `bcrypt==4.0.1`, `python-jose[cryptography]`, `python-dotenv`.
- Env (repo root): `.env` / `.env.example` with `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
- TinyDB auth store: `data/process/auth/auth.json` (gitignored) via `users_table` / `profiles_table` in `services/app/core/database.py`.
- Models: `services/app/models/user.py` (`UserRole`, create/update/public, login/token), `services/app/models/profile.py`.
- Domain: `user_service.py` (CRUD + `authenticate_user`), `profile_service.py` (get/update by `user_id`).
- Security: `services/app/core/security.py` (bcrypt hash/verify, JWT create/decode).
- Deps: `services/app/core/deps.py` — `OAuth2PasswordBearer`, `get_current_user`, `require_self_or_admin`.
- Routers registered in `main.py`:
  - `/users` — `POST /users` public; `GET/PUT/DELETE` require Bearer; PUT/DELETE require self or admin; only admin may change `role`.
  - `/auth` — `POST /auth/login`, `GET /auth/me` (protected).
  - `/profiles` — `GET/PUT /profiles/me` (protected).
  - `/suppliers` — all six routes require Bearer (meets AUTH-01 “≥5 existing routes” requirement).
- User and Profile remain in TinyDB only (no Supabase/SQL user tables).
- Known gap (non-blocking): Swagger Authorize OAuth2 form vs JSON login mismatch; use curl/`Authorization: Bearer` for manual checks. Backoffice does not send tokens yet (expected 401 on suppliers until frontend phase).

## Recently Completed (Documentation Context Setup)
- Created Memory Bank baseline:
  - `memory-bank/projectbrief.md`
  - `memory-bank/techContext.md`
  - `memory-bank/progress.md`
- Created governance documentation for AI agents:
  - Root `AGENTS.md` policy file.
  - Focused rule files in `.agents/rules/`.

## Recently Completed (services/api → services/app refactor)
- Migrated FastAPI package from `services/api/` to layered `services/app/`:
  - `core/` — TinyDB (`database.py`) and supplier seed (`seed.py`)
  - `models/supplier.py` — supplier Pydantic models/enums
  - `domain/` — `supplier_service.py`, `incident_service.py` (thin wrapper over `incidents_analysis`)
  - `routers/` — HTTP-only `suppliers.py` and `incidents.py`
  - `main.py` — FastAPI entrypoint (`uvicorn services.app.main:app`)
- HTTP contracts unchanged: `/suppliers`, `/api/incidents/analyze`, `/api/incidents/results/export`.
- Runtime data paths unchanged: `data/process/suppliers/suppliers.json`, `data/process/results.csv`.
- Updated `pyproject.toml` seed entry to `services.app.core.seed:run_seed`.
- Updated operational docs: `services/README(.es).md`, `uis/backoffice/README(.es).md`, root `README(.es).md`, `docs/architecture/ARCHITECTURE_PROPOSAL(.es).md`, `lesson2learn/...cli-a-fastapi.md`, `bitacora.md`, and this memory-bank entry.

## Recently Completed (Supplier directory models)
- Pydantic enums and models in `services/app/models/supplier.py` for Milestone 09 supplier directory:
  - Enums: `Country`, `Currency`, `SupplierStatus`, `SupplierCategory`, `ComplianceAgreement`.
  - Models: `SupplierCreate`, `SupplierRateUpdate`, `SupplierStatusUpdate`, `Supplier`.
  - Enforces USA/USD and UK/GBP pairing via `model_validator`.

## Recently Completed (API structure)
- HealthCore FastAPI entrypoint at `services/app/main.py` (CORS for local backoffice origins).
- Incidents HTTP routes in `services/app/routers/incidents.py` (orchestration via `domain/incident_service.py`):
  - `POST /api/incidents/analyze` — multipart CSV → JSON summary; persists last run via `export_results` to `data/process/results.csv`.
  - `GET /api/incidents/results/export` — downloadable CSV of last analysis (`404` if none).
- Business logic remains in `services/incidents_analysis/` (no duplication in the router).

## Recently Completed (Supplier runtime data organization)
- Reorganized TinyDB runtime persistence for supplier directory:
  - from `data/suppliers.json`
  - to `data/process/suppliers/suppliers.json`
- TinyDB path is configured in `services/app/core/database.py` (ensures parent directory creation).
- Updated `.gitignore` to ignore runtime artifacts:
  - `data/process/results.csv`
  - `data/process/suppliers/suppliers.json`
- Verified API continuity after reorganization with `GET /suppliers` returning `200`.
- Restored ignore for `data/process/suppliers/suppliers.json` after it was accidentally re-tracked on `main`; file kept local-only via `git rm --cached`.

## Recently Completed (Incidents backoffice UI)
- Nav entry `Incidents` → `/incidents` in `uis/backoffice/components/layout/BackofficeShell.tsx`.
- Page `uis/backoffice/app/incidents/page.tsx` with CSV upload (drag/drop), analyze, summary panels, and CSV download.
- Client `uis/backoffice/lib/services/healthcoreApi.ts` targets `NEXT_PUBLIC_HEALTHCORE_API_URL` (default `http://127.0.0.1:8000`); Tracker client unchanged.
- Types in `uis/backoffice/types/incidents.ts` use CONTEXT category/status/invalid rule names.

## Recently Completed (Supplier directory backoffice UI)
- Added nav entry `Suppliers` in `uis/backoffice/components/layout/BackofficeShell.tsx`.
- Added route `uis/backoffice/app/suppliers/page.tsx`.
- Implemented supplier module in `uis/backoffice/components/SuppliersWorkspace.tsx`:
  - list from `GET /suppliers`
  - client-side filters by country/category
  - loading, error, and empty states
  - optimistic in-memory refresh after create/rate/status actions
- Added create form `uis/backoffice/components/forms/SupplierForm.tsx` with basic client validation.
- Added `uis/backoffice/lib/services/suppliersApi.ts` and `uis/backoffice/hooks/useSuppliers.ts`.
- Added supplier types and labels in `uis/backoffice/types/suppliers.ts`.
- Verified with `cd uis/backoffice && npm run build` (route `/suppliers` generated successfully).

## Recently Completed (Architecture Migration)
- Migrated internal UI app path from `uis/talent-pipeline-tracker` to `uis/backoffice`.
- Added a new public Next.js app at `uis/website` (App Router, componentized sections, and intake form route).
- Added backoffice dashboard landing and module navigation:
  - Dashboard, Patients, Appointments, Billing, Claims, Reports.
- Integrated Hito 2 utilities in backoffice dashboard via direct imports from root `src/` (no business logic duplication).
- Prepared scalable backend service placeholders under `services/`.
- Updated repository documentation for new UI/service boundaries.
- Removed retired root static website/playground artifacts after the UI migration to `uis/website` and `uis/backoffice`.

## In-Scope Baselines from Context
- 12 clinics across US/UK.
- ~200 employees.
- Reported no-show baseline: 22%.
- Reported claim rejection baseline: 14%.
- Dual compliance obligations: HIPAA and UK GDPR.

## Assumptions and Constraints
- `CONTEXT.md` is the business source of truth.
- `company-choise.md` remains out of scope until explicit developer authorization.
- Missing details must be tracked as TODOs, not inferred.

## Open TODOs
- TODO: Confirm whether the intended restricted filename is `company-choise.md` only or also similarly named files.
- TODO: Confirm repository-wide command matrix for lint/test/build across all workspaces.
- TODO: Add milestone-by-milestone acceptance criteria if formally defined by maintainers.

## Next Documentation Maintenance Rules
- Update this file after any major implementation or policy change.
- Keep entries factual, timestamp-friendly, and short.
- Prefer explicit references to actual files over general statements.
