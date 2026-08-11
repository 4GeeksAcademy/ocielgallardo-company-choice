# HealthCore Backoffice

Internal Next.js application for HealthCore employees.

## Purpose

- Provide a dedicated internal workspace separated from the public website.
- Preserve and host the existing People & Talent candidate tracker.
- Expose Hito 2 TypeScript business logic utilities through interactive dashboard demos.
- Host patient incident CSV analysis against the local HealthCore FastAPI.

## Current sections

- `/` Dashboard
- `/login` Sign-in (JWT → `localStorage`)
- `/register` Sign-up (`POST /users` + automatic login)
- `/forgot-password` Request password-reset email
- `/reset-password` Set new password from email token (`?token=`)
- `/patients` Placeholder module
- `/appointments` Placeholder module
- `/billing` Placeholder module
- `/claims` Placeholder module
- `/reports` Placeholder module
- `/incidents` Patient incident CSV analysis (upload, summary, CSV download)
- `/suppliers` Supplier directory (list, filters, create, rate update, status update)
- `/applications` Candidate pipeline list and create form
- `/candidates/[id]` Candidate detail, edit, stage/status controls, notes
- `/account/profile` Account profile (email + name/phone/address)
- `/account/change-password` Change password while signed in

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

## Patient incidents (`/incidents`)

Uses the same backend pipeline as the CLI (`services/incidents_analysis/`), exposed by FastAPI.

### What you need running

Two processes:

1. **HealthCore API** (repo root) — default `http://127.0.0.1:8000`
2. **This backoffice** — usually `http://localhost:3000` (or `3001` if 3000 is taken)

```bash
# Terminal A — from repository root
python -m pip install fastapi uvicorn python-multipart   # once
python -m uvicorn services.app.main:app --reload

# Terminal B — this app
cd uis/backoffice
npm install   # once
npm run dev
```

Open the UI URL printed by Next (for example `http://localhost:3001/incidents` if port 3000 is busy).

Swagger for the API: `http://127.0.0.1:8000/docs`

### How to analyze a CSV

1. In the nav, open **Incidents**.
2. Drag/drop or select a `.csv` (sample: `data/raw/incidents-healthcore.csv` at repo root).
3. Click **Analyze CSV**.
4. Review totals, invalid-rule breakdown, category/status breakdowns, and satisfaction.
5. Click **Download results CSV** to fetch the last analysis from `GET /api/incidents/results/export`.

Expected with the official sample: **100** total / **94** valid / **6** invalid; satisfaction average **3.58**.

### API base URL

Client: `lib/services/healthcoreApi.ts`

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

### Related files

| Path | Role |
| --- | --- |
| `app/incidents/page.tsx` | Page: upload → analyze → summary → download |
| `components/incidents/IncidentCsvUpload.tsx` | File picker + drag and drop |
| `components/incidents/IncidentAnalysisSummary.tsx` | CONTEXT-aligned metrics UI |
| `lib/services/healthcoreApi.ts` | `POST /api/incidents/analyze`, `GET .../results/export` |
| `types/incidents.ts` | TypeScript shapes for the JSON summary |

Business rules live in `services/incidents_analysis/` (not duplicated here). Tracker traffic still uses `lib/services/client.ts` (4Geeks API).

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

For incident analysis, also start the API (see [Patient incidents](#patient-incidents-incidents) above).

## Build

```bash
npm run build
npm start
```

## Notes

- Candidate API integration uses the 4Geeks Talent Tracker API (`/records`).
- Incident analysis uses the local HealthCore FastAPI (`services/app`).
- HealthCore auth: login/register/forgot/reset/change-password live in this backoffice; the public website does not use JWT.
- `next.config.ts` enables external directory imports to consume root Hito 2 utilities.

> Spanish version: [README.es.md](./README.es.md).
