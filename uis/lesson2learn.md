# Lesson to learn — Talent Pipeline Tracker

What you should study to build this app on your own, why each decision matters, and what we implemented in this session.

---

## What you should learn

### 1. React and Next.js (App Router)

- **Client components** (`"use client"`) for interactivity: forms, filters, API calls from the browser.
- **File-based routing**: `app/applications/page.tsx`, `app/candidates/[id]/page.tsx`.
- **`useSearchParams`** for filters in the URL (shareable links, back/forward friendly).
- **`Suspense`** when using `useSearchParams` in client components.

### 2. TypeScript for API contracts

- Define types (`Application`, `Note`, `RecordCreateInput`) that mirror the API response.
- Catch mismatches at compile time instead of debugging in production.

### 3. HTTP and REST semantics

| Method | When to use | Example in this app |
|--------|-------------|---------------------|
| GET | Read data | List records, fetch one record, list notes |
| POST | Create a resource | New application, new note |
| PUT | Replace full resource | Edit candidate profile fields |
| PATCH | Partial update | Change only `status` or `stage` |
| DELETE | Remove resource | Delete a note |

Understanding **PUT vs PATCH** is essential: editing a form sends all fields (PUT); changing a dropdown sends only what changed (PATCH).

### 4. Fetch API and a thin client layer

- Centralize `fetch` in `lib/api/client.ts` (base URL, headers, error handling).
- Split by domain: `records.ts`, `notes.ts`.
- Throw typed errors (`ApiError`) so UI can show meaningful messages.

### 5. Form validation and UX feedback

- Validate **before** calling the API (required fields, email format, numeric experience).
- Show field-level errors (`aria-invalid`, `role="alert"`).
- Show success/error after submit (`aria-live="polite"`).
- When navigation happens on success (create → detail page), pass feedback via query param (`?created=1`) instead of losing the message.

### 6. State management patterns

- **Optimistic updates** for status/stage: update UI immediately, rollback on failure.
- **Local state** for lists after mutations (prepend new note, filter after delete).
- **Loading / error / empty** states for every async view.

### 7. Tailwind CSS

- Utility classes for layout, spacing, and accessible color contrast.
- Responsive grids (`sm:grid-cols-2`) for forms and detail panels.

### 8. Accessibility basics

- Labels linked to inputs (`htmlFor` / `id`).
- Live regions for dynamic feedback.
- Semantic HTML (`article`, `section`, `role="alert"`).

---

## Why build it this way

### Separate API layer (`lib/api/`)

**Why:** One place to change the base URL, auth headers, or error parsing. Components stay focused on UI.

### Dedicated detail route (`/candidates/[id]`)

**Why:** Deep links (share a candidate URL), clear separation between list workspace and detail workspace, and a natural place to load `GET /records/:id` plus notes in parallel.

### Client-side filtering

**Why:** The API returns up to 100 records; filtering by status, stage, and search in the browser avoids extra round-trips and keeps the UI instant. For larger datasets you would move filters to query params on the API.

### PATCH for pipeline fields, PUT for profile edit

**Why:** Matches REST intent and reduces risk of overwriting unrelated fields when only status or stage changes.

### Validation in the form component

**Why:** Immediate feedback without a network call. Server-side validation still applies on the API; the client layer improves UX and reduces bad requests.

### Re-throw errors from parent handlers

**Why:** `ApplicationForm` and `NoteForm` catch errors to show inline messages. If the parent swallows the error, the form never knows the request failed.

### Flash message after create redirect

**Why:** On successful `POST /records`, we navigate to the detail page. Showing success there (`?created=1` → banner) is more reliable than a message on a page that unmounts.

---

## What we did in this session

### Verification

Confirmed the app already covered the full checklist:

- Status and stage controls → `PATCH /records/:id`
- Notes list, create, delete → `GET`, `POST`, `DELETE` on `/records/:id/notes`
- Create form → `POST /records` on `/applications`
- Edit form → `PUT /records/:id` on `/candidates/[id]`
- Required-field validation in `ApplicationForm`

### Improvements added

1. **Create success feedback** — redirect to `/candidates/:id?created=1` and show a success banner on the detail page.
2. **Edit error/success feedback** — banner on detail page; errors re-thrown so the form can also show a message while still open.
3. **Note delete errors** — `NotesSection` shows an alert if `DELETE` fails.
4. **Error propagation** — `handleCreate`, `handleAddNote`, and `handleDeleteNote` re-throw so child forms handle failures correctly.
5. **Documentation** — updated `uis/README.md`, `uis/README.es.md`, and this file.

### Key files

| File | Role |
|------|------|
| `components/ApplicationsWorkspace.tsx` | List, filters, create form |
| `components/candidates/CandidateDetailWorkspace.tsx` | Detail page orchestration |
| `components/detail/ApplicationDetailPanel.tsx` | Status/stage, notes, CV link |
| `components/forms/ApplicationForm.tsx` | Create/edit with validation |
| `components/forms/NoteForm.tsx` | Add note with validation |
| `lib/api/records.ts` | CRUD + PATCH for records |
| `lib/api/notes.ts` | Notes CRUD |

---

## Suggested practice path

1. Read the [Talent Tracker API docs](https://playground.4geeks.com/tracker/api/v1/docs) and call endpoints with `curl` or Postman.
2. Build a minimal page that only lists records (`GET /records`).
3. Add one mutation at a time (create → patch status → notes).
4. Add validation and loading states last — they are easier once the happy path works.
5. Compare your approach with this codebase and note what you would simplify or extend (pagination, auth, tests).
