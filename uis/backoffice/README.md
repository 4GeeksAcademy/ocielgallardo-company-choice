# HealthCore Backoffice

Internal Next.js application for HealthCore employees.

## Purpose

- Provide a dedicated internal workspace separated from the public website.
- Preserve and host the existing People & Talent candidate tracker.
- Expose Hito 2 TypeScript business logic utilities through interactive dashboard demos.
- Prepare boundaries for future operational modules.

## Current sections

- `/` Dashboard
- `/patients` Placeholder module
- `/appointments` Placeholder module
- `/billing` Placeholder module
- `/claims` Placeholder module
- `/reports` Placeholder module
- `/applications` Candidate pipeline list and create form
- `/candidates/[id]` Candidate detail, edit, stage/status controls, notes

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

## Build

```bash
npm run build
npm start
```

## Notes

- Candidate API integration uses the 4Geeks Talent Tracker API (`/records`).
- `next.config.ts` enables external directory imports to consume root Hito 2 utilities.
