# Language check — docs and UI (2026-10-31)

**Scope:** report only. Nothing is translated in this PR. Code, UI strings and existing docs are unchanged.
**Baseline:** `main` @ `143c08d`.
**Convention checked:**

- Documentation is in **English** (`README.md` and topic docs).
- Spanish lives only in **intentional translations** named `*.es.md`, which are linked from the English file (for example `docs/README.md` → `README.es.md`).
- User-facing UI (backoffice + website) is in **English**. The backoffice was translated in commit `697ad4e`.

**Method:**

- All 135 tracked Markdown files were scanned outside `node_modules/` and `.next/`, skipping fenced code blocks.
- A line counted as Spanish or English by word-frequency ratio (`wordfreq`) and accents. A file was flagged as an inconsistency when an English file had ≥ 15 % Spanish lines, or an `.es.md` file had < 50 % Spanish lines.
- The UI (`uis/backoffice`, `uis/website`, `*.ts/*.tsx`) got a string-literal and JSX-text scan, plus an accent search.
- Every hit was reviewed by hand. The false positives were `en-US`, the "Hito" proper noun, and `lang="en"`.

Result: the backoffice and website UIs are almost fully English (2 leftover strings). The docs follow the convention in most folders. Inconsistencies are concentrated in `docs/audit/`, a few root-level files, and twin naming.

---

## 1. UI — leftover Spanish user-facing strings

| File:line | Text | Suggested English |
|-----------|------|-------------------|
| `uis/backoffice/components/rfp/RfpIntakePanel.tsx:387` | `` `Reintento encolado (${created.status}).` `` | `` `Retry enqueued (${created.status}).` `` |
| `uis/backoffice/components/applications/ApplicationList.tsx:65` | `Reintentar` (button) | `Retry` |

`uis/website`: no Spanish user-facing strings found.

### Backend strings that reach users (not UI code, but user-visible)

| File:line | Text | Note |
|-----------|------|------|
| `services/app/domain/password_reset_service.py:103-108` | Subject `HealthCore: Restablecer contraseña` + Spanish HTML body | Password-reset email is in Spanish while the backoffice is English. Decide on one language, or localize by user preference. |
| `services/app/core/inventory_seed.py:24-52` | Product names such as `Mascarilla quirúrgica (pack de 50)`, `Apósito adhesivo para heridas`, `Solución salina 0,9% 500ml` | Seed **data** shown in the English Inventory UI. Data, not code. Change it only through a new seed, never by rewriting existing rows. |

## 2. English docs that contain Spanish (no `.es.md` twin)

| File | Spanish share | Examples |
|------|---------------|----------|
| `docs/audit/README.md` | ~36 % | Intro "Evidencia y documentación de auditorías técnicas…"; table headers `Documento` / `Contenido`; "Extraer métricas"; section "Evidencia Lighthouse" |
| `docs/audit/REPORT.md` | ~45 % | Title "Informe de auditoría de rendimiento", "**Hito:** Auditoría de Rendimiento Frontend". The index describes it as "Informe en español". If intentional, rename it to `REPORT.es.md` and add an English `REPORT.md`. |
| `docs/audit/after/README.md` | ~36 % | "## Segunda pasada (2026-08-28) — Docker producción", "el entorno local sigue siendo algo inestable…" |
| `docs/audit/final/README.md` | ~56 % | "**Diferencia vs `docs/audit/after/`:** la pasada del 2026-08-28 midió código…", "Chrome **Incógnito** (evitar IndexedDB / extensiones)" |
| `docs/audit/serialization-audit.md` | ~18 % | Column headers `Estado original`, `Schema original`, `Problema detectado`, `Estado actual`; category values `Ya serializado`, `Parcialmente serializado` (also echoed in `docs/audit/README.md`: "31/31 endpoints Ya serializado") |
| `CONTEXT.md` (repo root) | ~96 % | Whole file in Spanish ("HealthCore es una empresa sanitaria…") |
| `bitacora.md` (repo root) | ~68 % | Spanish work log (the file name itself is Spanish) |
| `company-choice.md` (repo root) | 100 % | "-Empresa: HealthCore…", "-Razón de la elección…" |
| `stitch_healthcore_design_system/healthcore_design_system_design.md` | ~81 % | "**Proyecto:** Unidad interna de transformación digital…" |

Root files `CONTEXT.md`, `bitacora.md`, and `company-choice.md` look like 4Geeks course deliverables. If they must stay in Spanish, rename them `*.es.md` (or add an English twin) so they match the convention.

## 3. English docs that reference old Spanish UI labels (stale after `697ad4e`)

| File:line | Stale label | Current UI label |
|-----------|-------------|------------------|
| `uis/backoffice/README.md:16` | "next to Cerrar sesión" | `Log out` (`components/layout/AccountMenu.tsx:117`) |
| `uis/backoffice/README.md:50` | "Nav: Suministros, Registrar entrega, Registrar consumo, Historial de órdenes." | `Supplies`, `Log delivery`, `Log usage`, `Order history` (`components/layout/navConfig.ts:62-65`) |
| `uis/backoffice/README.md:160` | "**Cerrar sesión**" | `Log out` |
| `docs/audit/CACHING_REPORT.md:142` | "Historial / Suministros, or clicking Actualizar" | `Order history` / `Supplies` / `Refresh` |
| `docs/audit/serialization-audit.md:64` | "Historial con campos extra…" | Order history |

`uis/backoffice/README.es.md` is a translation, so Spanish labels there are fine. It should still mention that the UI itself is now English.

## 4. Spanish translations (`.es.md`) that are not translated

| File | Finding |
|------|---------|
| `docs/incident-manager/CONTEXT-HealthCore.es.md` | 0 % Spanish: the content is the English text ("# CONTEXT — Centralized Incident Manager…"), a copy of `CONTEXT-HealthCore.md`. |
| `docs/sales-forecasting/ROADMAP.es.md` | Spanish file with **no English counterpart** (`ROADMAP.md` is missing). |

Partly translated (acceptable, but worth a pass): `uis/backoffice/README.es.md` (~52 % Spanish lines, with many untranslated English bullets), `docs/telemetry/telemetry-plan.es.md` (~64 %), `services/README.es.md` (~60 %), and `mcps/incidents-inventory-mcp/README.es.md` (~64 %).

## 5. Naming / structure inconsistencies

1. **Two twin-naming schemes:**
   - Most folders use `X.md` + `X.es.md`.
   - These folders use `X.en.md` + `X.es.md` with no plain `X.md`:
     - `docs/company-knowledge-base/*.en.md`
     - `docs/inventory/CONTEXT-HealthCore.en.md`
     - `docs/rag/training-rag/CONTEXT—HealthCore.en.md`
     - `docs/sales-forecasting/CONTEXT-healthcore.en.md`
   - The company-knowledge-base pair may be intentional (RAG corpus files per language). The others should follow `X.md` + `X.es.md`.
2. **`README.md` without a `README.es.md` twin:**
   - `docs/audit/`
   - `docs/company-knowledge-base/`
   - `docs/rpf-request/rfp-requests/healthcore/`
   - `packages/shared/`
   - `services/_template-service/`
   - `services/clinical-operations/`
   - `services/compliance/`
   - `services/gateway/`
   - `services/incidents_analysis/`
   - `services/revenue-cycle/`
3. **Topic folders under `docs/` without any README:**
   - `agentic-workflow`
   - `architecture`
   - `backoffice`
   - `data-contract`
   - `data-pipelines`
   - `incident-manager`
   - `inventory`
   - `mcp`
   - `memory-and-harness`
   - `rag`
   - `rpf-request`
   - `sales-forecasting`
   - `supplier-directory`
   - `telemetry`
   
   This is only a convention gap if "a README in every folder" is the rule. `docs/README.md` already indexes them.
4. **Folder name typo:** `docs/rpf-request/` should probably be `docs/rfp-request/`. Renaming it breaks links, so it needs a link sweep first.
5. **Spanish words inside English docs:**
   - `docs/README.md:40`: "MCP server (**hito** 25)". Use "milestone 25".
   - The same word appears in other English docs as "Hito" ("Milestone").
6. Not on `main` but pending in PR #52 (`feature/sse-notifications` → `feature/rfp-approval-completion`):
   - `docs/real-time-notification/heathcore-BRIFING.md` / `.es.md` have the typos "heathcore" and "BRIFING". Elsewhere the repo uses `healthcore-BRIEFING.md`.

## 6. Already consistent (no action)

- The root `README.md`/`README.es.md`, and every `agents/`, `data/*`, `infra/`, `internal/`, `mcps/`, `packages/`, `scripts/`, `services/`, `uis/`, `uis/website` README pair: English file in English, Spanish twin in Spanish.
- These docs are English-only with no Spanish:
  - `docs/architecture`
  - `docs/agentic-workflow`
  - `docs/data-contract`
  - `docs/data-pipelines`
  - `docs/memory-and-harness`
  - `docs/rpf-request`
  - `docs/supplier-directory`
  - `docs/telemetry`
  - `docs/mcp`
  - `docs/rag`
  - `docs/backoffice/UI-UX-IMPROVEMENT.md`
  - `docs/audit/AUDIT.md`
- `lesson2learn/` and `memory-bank/` are English (internal notes, no twins expected).

## 7. Suggested follow-up (separate PRs, docs-only unless noted)

1. `fix(i18n)`: the two backoffice strings in §1. Code change: 2 lines.
2. `docs(audit)`: translate `docs/audit/README.md`, `after/README.md`, and `final/README.md`, plus the serialization-audit headers, to English. Move `REPORT.md` to `REPORT.es.md` and add an English `REPORT.md`.
3. `docs(backoffice)`: update the stale labels in `uis/backoffice/README.md` and `docs/audit/CACHING_REPORT.md`.
4. `docs`: translate `docs/incident-manager/CONTEXT-HealthCore.es.md`, and add `docs/sales-forecasting/ROADMAP.md`.
5. Decide the policy for the root course files (`CONTEXT.md`, `bitacora.md`, `company-choice.md`) and for the `.en.md` naming. Then rename in one link-checked PR.
6. Product decision: the language of the password-reset email and the inventory seed names.
