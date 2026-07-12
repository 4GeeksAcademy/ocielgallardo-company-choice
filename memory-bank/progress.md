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
