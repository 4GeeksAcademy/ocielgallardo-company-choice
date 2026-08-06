# HealthCore Backoffice

Internal Next.js application for HealthCore employees.

## Purpose

- Provide a dedicated internal workspace separated from the public website.
- Preserve and host the existing People & Talent candidate tracker.
- Expose Hito 2 TypeScript business logic utilities through interactive dashboard demos.
- Host patient incident CSV analysis against the local HealthCore FastAPI.

## Current sections

- `/` Dashboard
- `/patients` Placeholder module
- `/appointments` Placeholder module
- `/billing` Placeholder module
- `/claims` Placeholder module
- `/reports` Placeholder module
- `/incidents` Patient incident CSV analysis (upload, summary, CSV download)
- `/suppliers` Supplier directory (list, filters, create, rate update, status update)
- `/applications` Candidate pipeline list and create form
- `/candidates/[id]` Candidate detail, edit, stage/status controls, notes

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
- `next.config.ts` enables external directory imports to consume root Hito 2 utilities.

> Spanish version: [README.es.md](./README.es.md).
