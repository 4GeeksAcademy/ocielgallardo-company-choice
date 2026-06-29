# `uis` folder

This folder contains **all the user interfaces** related to the company for the cross-functional AI Engineering project (for example: web applications, internal dashboards, customer portals, Streamlit/Gradio apps, etc.).

Each subfolder inside `uis/` must correspond to **one specific user interface** (for example: `website`, `backoffice`) and include its own technical and functional documentation.

- **Main purpose**: to centralize in a single place all the frontend applications that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the applications you add, their objective, the technology used, and how to run them.

> _Spanish version: [README.es.md](./README.es.md)._

## Interfaces

### `talent-pipeline-tracker`

Internal **People & Talent** tool for managing the HealthCore candidate pipeline.

- **Technology**: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- **API**: [Talent Tracker API](https://playground.4geeks.com/tracker/api/v1/docs) (`/records`, not `/applications`)
- **Routes**:
  - `/applications` — list, filters, and create form
  - `/candidates/[id]` — candidate detail, edit, status/stage, and notes

**Run:**

```bash
cd uis/talent-pipeline-tracker
npm install
npm run dev
```

#### Feature checklist (API integration)

| Area | Requirement | Implementation |
|------|-------------|----------------|
| **Detail** | Update status via `PATCH /records/:id` | `StatusStageControls` → `patchRecord()` |
| **Detail** | Update stage via `PATCH /records/:id` | `StatusStageControls` → `patchRecord()` |
| **Detail** | List notes via `GET /records/:id/notes` | `fetchNotes()` on candidate load |
| **Detail** | Add note via `POST /records/:id/notes` | `NoteForm` → `createNote()` |
| **Detail** | Delete note via `DELETE /records/:id/notes/:note_id` | `NotesSection` → `deleteNote()` |
| **Applications** | Create via `POST /records` | `ApplicationForm` (create) on `/applications` |
| **Applications** | Edit via `PUT /records/:id` | `ApplicationForm` (edit) on `/candidates/[id]` |
| **Forms** | Required-field validation before submit | `ApplicationForm.validateForm()` |
| **Forms** | Success/error feedback after submit | Inline messages + flash banner on detail page |

Detailed documentation in [`talent-pipeline-tracker/README.md`](./talent-pipeline-tracker/README.md).  
Learning notes in [`lesson2learn.md`](./lesson2learn.md) (Spanish).

## Update — June 2026

### Summary

Full implementation of the **Talent Pipeline Tracker** for **HealthCore** (**People & Workforce** area, Diane Foster). The app consumes the [Talent Tracker API](https://playground.4geeks.com/tracker/api/v1/docs) and supports clinical hiring pipeline management across HealthCore’s 12 clinics.

### Routes

| Route | Description |
|-------|-------------|
| `/applications` | List, filters, search, and new application form |
| `/candidates/[id]` | Detail, edit, status/stage, notes, and CV link |

### API integration

| Operation | Endpoint | Where |
|-----------|----------|-------|
| List applications | `GET /records` | `/applications` |
| View detail | `GET /records/:id` | `/candidates/[id]` |
| Create application | `POST /records` | Form on `/applications` |
| Edit profile data | `PUT /records/:id` | Form on `/candidates/[id]` |
| Update status or stage | `PATCH /records/:id` | Controls on detail view |
| List notes | `GET /records/:id/notes` | Notes section |
| Add note | `POST /records/:id/notes` | Note form |
| Delete note | `DELETE /records/:id/notes/:note_id` | Button on each note |

### Features delivered

- List with status/stage badges, URL-based filters, and client-side name/email search.
- Create and edit forms with required-field validation and success/error feedback.
- Pipeline controls with optimistic updates (no full page reload).
- Internal notes CRUD with validation and error handling on create/delete.
- CV link when `cv_url` is available.
- Async UI states: **loading**, **success**, and **error** (with retry) for list, detail, and notes.
- After `POST`, `PUT`, and `PATCH`, the UI updates on the client without `location.reload()`.

### Architecture

- **Stack:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4.
- **State:** React hooks (`useState`, `useEffect`, `useCallback`) — no Redux, Zustand, or Jotai.
- **Structure:** `components/`, `hooks/`, `types/`, `lib/services/`, `lib/constants/`, `lib/utils/`.
- **Services:** `lib/services/` layer with centralized `async/await` (`client`, `records`, `notes`).
- **Hooks:** `useRecords`, `useCandidateDetail`, `useDebouncedValue`.
- **Types:** `types/application.ts` (API) and `types/async.ts` (loading states).

### Company context

The UI is tailored to **HealthCore** and the **People & Talent** team (Diane Foster). API field names follow the tracker backend (`full_name`, `status`, `stage`, etc.); visible labels are in Spanish and aligned with the HR pipeline.
