# Progress

## Current Status Snapshot
- Business context source established in `CONTEXT.md`.
- Web deliverables for Milestone 1 are implemented.
- Core TypeScript domain/utilities for Milestone 2 are implemented.
- Manual browser playground for utility inspection is available.
- Type-level model validation command is available in `packages/shared`.

## Recently Completed (Documentation Context Setup)
- Created Memory Bank baseline:
  - `memory-bank/projectbrief.md`
  - `memory-bank/techContext.md`
  - `memory-bank/progress.md`
- Created governance documentation for AI agents:
  - Root `AGENTS.md` policy file.
  - Focused rule files in `.agents/rules/`.

## Recently Completed (Supplier directory models)
- Pydantic enums and models in `services/api/models.py` for Milestone 09 supplier directory:
  - Enums: `Country`, `Currency`, `SupplierStatus`, `SupplierCategory`, `ComplianceAgreement`.
  - Models: `SupplierCreate`, `SupplierRateUpdate`, `SupplierStatusUpdate`, `Supplier`.
  - Enforces USA/USD and UK/GBP pairing via `model_validator`.

## Recently Completed (API structure)
- HealthCore FastAPI entrypoint at `services/api/main.py` (CORS for local backoffice origins).
- Incidents HTTP routes in `services/api/routers/incidents.py`:
  - `POST /api/incidents/analyze` — multipart CSV → JSON summary; persists last run via `export_results` to `data/process/results.csv`.
  - `GET /api/incidents/results/export` — downloadable CSV of last analysis (`404` if none).
- Business logic remains in `services/incidents_analysis/` (no duplication in the router).

## Recently Completed (Supplier runtime data organization)
- Reorganized TinyDB runtime persistence for supplier directory:
  - from `data/suppliers.json`
  - to `data/process/suppliers/suppliers.json`
- Updated `services/api/database.py` to point to the new runtime path and ensure parent directory creation.
- Updated `.gitignore` to ignore runtime artifacts:
  - `data/process/results.csv`
  - `data/process/suppliers/suppliers.json`
- Verified API continuity after reorganization with `GET /suppliers` returning `200`.

## Recently Completed (Incidents backoffice UI)
- Nav entry `Incidents` → `/incidents` in `uis/backoffice/components/layout/BackofficeShell.tsx`.
- Page `uis/backoffice/app/incidents/page.tsx` with CSV upload (drag/drop), analyze, summary panels, and CSV download.
- Client `uis/backoffice/lib/services/healthcoreApi.ts` targets `NEXT_PUBLIC_HEALTHCORE_API_URL` (default `http://127.0.0.1:8000`); Tracker client unchanged.
- Types in `uis/backoffice/types/incidents.ts` use CONTEXT category/status/invalid rule names.

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
