# uis

This directory contains frontend applications in the monorepo.

## Applications

### website

Public Next.js application for HealthCore external communication.

- Purpose: landing pages and patient application intake flow.
- Stack: Next.js 16, React 19, TypeScript, Tailwind CSS 4.
- Routes:
  - `/` public landing
  - `/application` intake form with client-side validation

Run:

```bash
cd uis/website
npm install
npm run dev
```

### backoffice

Internal Next.js application for HealthCore employees.

- Purpose: internal operations workspace and module shell.
- Includes the existing People & Talent candidate pipeline (migrated from `uis/talent-pipeline-tracker`).
- Integrates Hito 2 TypeScript business utilities directly from root `src/` (no duplicated business logic).
- Primary sections:
  - Dashboard
  - Login / Register (AUTH-02: JWT in `localStorage`, Bearer on HealthCore calls)
  - Patients
  - Appointments
  - Billing
  - Claims
  - Reports
  - Incidents / Suppliers
  - People & Talent (`/applications`, `/candidates/[id]`)
- Public `website` remains without authentication.

Run:

```bash
cd uis/backoffice
npm install
npm run dev
```

## Boundaries

- Keep public-facing functionality in `website`.
- Keep employee-only workflows in `backoffice`.
- Reuse shared domain logic from root `src/` and shared packages.
- Avoid duplicating business rules between UI applications.
