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
