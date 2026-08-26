# HealthCore Backoffice

Internal Next.js application for HealthCore employees.

## Purpose

- Provide a dedicated internal workspace separated from the public website.
- Preserve and host the existing People & Talent candidate tracker.
- Expose Hito 2 TypeScript business logic utilities through interactive dashboard demos.
- Host the centralized incident manager (register, list, summary) and CSV analysis against the local HealthCore FastAPI.

## Current sections

- `/` Dashboard
- `/login` Sign-in (JWT → `localStorage`)
- `/register` Sign-up (`POST /users` + automatic login)
- `/forgot-password` Request password-reset email
- `/reset-password` Set new password from email token (`?token=`)
- `/incidents` Incident manager list (filters + status updates)
- `/incidents/new` Register a new incident (PHI warning on description)
- `/incidents/summary` Aggregated metrics by status/category/origin/branch
- `/incidents/analyze` Patient incident CSV analysis (upload, summary, CSV download)
- `/suppliers` Supplier directory (list, filters, create, rate update, status update)
- `/inventory/products` Medical supplies with current stock (level badges)
- `/inventory/orders/inbound` Register a vendor delivery
- `/inventory/orders/outbound` Register clinical consumption (reactive stock + over-stock warning)
- `/inventory/orders` Order history (read-only)
- `/applications` Candidate pipeline list and create form
- `/candidates/[id]` Candidate detail, edit, stage/status controls, notes
- `/account/profile` Account profile (email + name/phone/address)
- `/account/change-password` Change password while signed in

## Inventory (`/inventory`)

Four authenticated views against `GET/POST /inventory/*` (Bearer). Contract: `docs/inventory/CONTEXT-HealthCore.en.md`. Client: `lib/services/inventoryApi.ts`.

| Path | Role |
| --- | --- |
| `/inventory/products` | Supply list with `current_stock` and visual levels (critical &lt; 5, low &lt; 15) |
| `/inventory/orders/inbound` | Delivery form (`POST /inventory/orders/inbound`) |
| `/inventory/orders/outbound` | Consumption form; shows selected product stock; client warning if quantity exceeds stock; `HTTP 400` inline on quantity |
| `/inventory/orders` | Delivery and consumption history (read-only) |

Nav: Suministros, Registrar entrega, Registrar consumo, Historial de órdenes.

## Supplier directory (`/suppliers`)

Uses the local HealthCore FastAPI supplier endpoints exposed by `services/app`.

### What the UI supports

1. Loads suppliers from `GET /suppliers`.
2. Filters the list by country and category without page reload.
3. Registers a new supplier with client-side validation for required fields.
4. Shows API validation errors returned by the backend.
5. Updates `monthly_rate` with `PATCH /suppliers/{id}/rate`.
6. Updates `status` with `PATCH /suppliers/{id}/status`.
7. Visually distinguishes `active` and `suspended` suppliers.

### Related files

| Path | Role |
| --- | --- |
| `app/suppliers/page.tsx` | Supplier directory route |
| `components/SuppliersWorkspace.tsx` | Main supplier UI orchestration |
| `components/forms/SupplierForm.tsx` | Create supplier form with client validation |
| `components/suppliers/SupplierStatusBadge.tsx` | Visual status badge |
| `hooks/useSuppliers.ts` | Supplier loading state and refresh |
| `lib/services/suppliersApi.ts` | `GET /suppliers`, `POST /suppliers`, supplier PATCH actions |
| `types/suppliers.ts` | Supplier types, options, labels, and helpers |

## Incident manager (`/incidents`)

Centralized incident registration and tracking for HealthCore clinics. Contract: `docs/incident-manager/CONTEXT-HealthCore.md`. UI labels are in **English**.

### Routes

| Path | Role |
| --- | --- |
| `/incidents` | List + filters (`status`, `origin`, `branch`) + inline status transitions with rollback on failure |
| `/incidents/new` | Create form; branch always required; branch highlighted when `origin === branch`; PHI warning before description |
| `/incidents/summary` | Totals from `GET /api/incidents/summary` (isolated loading/error) |
| `/incidents/analyze` | Legacy CSV analyzer UI (same pipeline as CLI) |

### What you need running

1. **HealthCore API** (repo root) — default `http://127.0.0.1:8000`
2. **This backoffice** — usually `http://localhost:3000` (or `3001`)

```bash
# Terminal A — from repository root
PYTHONPATH=packages/shared uv run uvicorn services.app.main:app --reload
# optional historical seed
PYTHONPATH=packages/shared uv run python scripts/seed_incidents.py

# Terminal B — this app
cd uis/backoffice
npm install   # once
npm run dev
```

Sign in first (manager endpoints require Bearer). Swagger: `http://127.0.0.1:8000/docs`

### Related files (manager)

| Path | Role |
| --- | --- |
| `app/incidents/page.tsx` | List workspace |
| `app/incidents/new/page.tsx` | Registration page |
| `app/incidents/summary/page.tsx` | Summary page |
| `components/incidents/IncidentListPanel.tsx` | Filters, table, status updates |
| `components/incidents/IncidentCreateForm.tsx` | Create form + PHI notice |
| `components/incidents/IncidentSummaryPanel.tsx` | Metric panels |
| `lib/services/incidentsManagerApi.ts` | Manager API client + friendly errors |
| `types/incidentManager.ts` | Manager types, options, labels |

## Patient incident CSV analysis (`/incidents/analyze`)

Uses the same backend pipeline as the CLI (`services/incidents_analysis/`), exposed by FastAPI. Validation rules live in `packages/shared/healthcore_shared` (re-exported by the analyzer package).

### How to analyze a CSV

1. Open **CSV analyzer** from the Incidents page (or `/incidents/analyze`).
2. Drag/drop or select a `.csv` (sample: `data/raw/incidents-healthcore.csv` at repo root).
3. Click **Analyze CSV**.
4. Review totals, invalid-rule breakdown, category/status breakdowns, and satisfaction.
5. Click **Download results CSV** to fetch the last analysis from `GET /api/incidents/results/export`.

Expected with the official sample: **100** total / **94** valid / **6** invalid; satisfaction average **3.58**.

### API base URL

Clients: `lib/services/healthcoreClient.ts`, `incidentsManagerApi.ts`, `healthcoreApi.ts`

- Default: `http://127.0.0.1:8000`
- Override: set `NEXT_PUBLIC_HEALTHCORE_API_URL` (restart `npm run dev` after changing it)
- Local file ready to edit: `uis/backoffice/.env.local`
- Commit-safe example: `uis/backoffice/.env.example`

If you open the UI through a published Codespaces URL instead of localhost, replace the value in `.env.local` with the published URL of the API port.

CORS on the API allows `localhost` / `127.0.0.1` on ports **3000** and **3001**. If Next uses another port, add that origin in `services/app/main.py`.

### Auth frontend (AUTH-02 / AUTH-03 — complete)

- `/login` and `/register`: JWT in `localStorage` (`healthcore_access_token`); redirect to `/`.
- Login includes “Forgot password?” → `/forgot-password`.
- `/forgot-password`: always shows a generic confirmation after submit (anti-enumeration). Calls `POST /auth/forgot-password` with `auth: false`.
- `/reset-password?token=...`: new password + confirmation → `POST /auth/reset-password`; success redirects to `/login?reset=success`.
- `/account/change-password`: current + new + confirmation → `POST /auth/change-password` (Bearer).
- `healthcoreClient.ts`: Bearer on calls; **401** → clear + `/login` (skipped on auth pages including forgot/reset).
- `AppChrome`: no shell on `/login`, `/register`, `/forgot-password`, `/reset-password`; no token elsewhere → `/login`.
- `/account/profile`: `GET /auth/me` + `PUT /profiles/me` (email read-only).
- Shell: Profile + Change password nav + **Cerrar sesión** (`clearSessionAndRedirectToLogin`).
- Public website has no auth. Runtime `data/process/auth/auth.json` is gitignored.
- Password emails are sent by the **API** (Resend). Configure root `.env` (`RESEND_API_KEY`, `EMAIL_FROM`, `FRONTEND_BASE_URL`); never put mail keys in `NEXT_PUBLIC_*`.

### Auth-related files

| Path | Role |
| --- | --- |
| `app/login/page.tsx` | Sign-in page (+ reset success banner) |
| `app/register/page.tsx` | Sign-up page |
| `app/forgot-password/page.tsx` | Forgot-password page |
| `app/reset-password/page.tsx` | Reset-password page (Suspense + token reader) |
| `app/account/profile/page.tsx` | Profile page |
| `app/account/change-password/page.tsx` | Change-password page |
| `components/forms/LoginForm.tsx` | Login → token → `/` |
| `components/forms/RegisterForm.tsx` | Register + password confirmation |
| `components/forms/ForgotPasswordForm.tsx` | Request reset email |
| `components/forms/ResetPasswordForm.tsx` | Submit new password with token |
| `components/forms/ChangePasswordForm.tsx` | Authenticated password change |
| `components/forms/ProfileForm.tsx` | Edit name/phone/address |
| `components/layout/AppChrome.tsx` | Route guard + shell |
| `components/layout/BackofficeShell.tsx` | Nav + logout |
| `lib/services/healthcoreClient.ts` | Token, Bearer, 401 |
| `lib/services/authApi.ts` | login, register, me, profile, forgot/reset/change password |
| `types/auth.ts` | Auth types |

### Related files (CSV analyze)

| Path | Role |
| --- | --- |
| `app/incidents/analyze/page.tsx` | Page: upload → analyze → summary → download |
| `components/incidents/IncidentCsvUpload.tsx` | File picker + drag and drop |
| `components/incidents/IncidentAnalysisSummary.tsx` | CONTEXT-aligned metrics UI |
| `lib/services/healthcoreApi.ts` | `POST /api/incidents/analyze`, `GET .../results/export` |
| `types/incidents.ts` | TypeScript shapes for the JSON summary |

Manager business rules live in `packages/shared/healthcore_shared` and `services/app/domain/incident_manager_service.py`. CSV analyze rules are shared (not duplicated in the UI). Tracker traffic still uses `lib/services/client.ts` (4Geeks API).

## Hito 2 integration

The dashboard imports utilities directly from root `src/`:

- `src/utils/collections.ts`
- `src/utils/search.ts`
- `src/utils/transformations.ts`
- `src/utils/validations.ts`
- `src/types/models.ts`

This preserves a single source of business logic with no duplication.

## Stack

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS 4

## Run

```bash
cd uis/backoffice
npm install
npm run dev
```

For the incident manager or CSV analysis, also start the API (see [Incident manager](#incident-manager-incidents) above).

## Build

```bash
npm run build
npm start
```

## Notes

- Candidate API integration uses the 4Geeks Talent Tracker API (`/records`).
- Incident manager and CSV analysis use the local HealthCore FastAPI (`services/app`).
- HealthCore auth: login/register/forgot/reset/change-password live in this backoffice; the public website does not use JWT.
- `next.config.ts` enables external directory imports to consume root Hito 2 utilities.

> Spanish version: [README.es.md](./README.es.md).
