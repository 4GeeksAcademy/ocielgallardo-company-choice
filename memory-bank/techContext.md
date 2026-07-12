# Technical Context

## Stack Summary
- Markup/UI: HTML (including responsive pages and semantic sections).
- Frontend logic: JavaScript for form validation and manual playground scripts.
- Domain and utilities: TypeScript (typed models and utility modules).
- Package tooling: npm scripts via `packages/shared/package.json`.

## Verified Technical Areas
- Root web pages: `index.html`, `application.html`, `test.html`.
- Frontend scripts: `validation.js`, `test-playground.js`, `test-data.js`.
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
- Service architecture placeholders:
  - `services/gateway`
  - `services/clinical-operations`
  - `services/revenue-cycle`
  - `services/compliance`

## Validation and Local Checks
- Type validation command (documented):
  - `cd /workspaces/ocielgallardo-company-choice/packages/shared`
  - `npm run test:types:models`

## Repository Navigation Guide
- `CONTEXT.md`: business domain baseline and company scenario.
- `memory-bank/`: persistent AI-agent context and progress tracking.
- `.agents/rules/`: behavior and contribution constraints for AI agents.
- `src/`: core typed models and utility logic.
- `uis/`: UI applications and interface-focused projects.
- `services/`: backend/API and workers (future or partial, depending on milestone).
- `data/`: data pipelines and evaluation-oriented assets.
- `skills/` and `agents/`: reusable AI workflows and templates.

## Folder Structure (High-Level)
- Monorepo-like educational structure with top-level domains for UI, services, workflows, data, and shared resources.
- Current implemented business logic remains concentrated in root `src/`.
- Public and internal UIs are now separated into independent apps under `uis/website` and `uis/backoffice`.

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
