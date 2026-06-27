# Carpeta `uis`

Esta carpeta contiene **todas las interfaces de usuario** relacionadas con la compañía para el proyecto transversal de AI Engineering (por ejemplo: aplicaciones web, dashboards internos, portales de clientes, apps de Streamlit/Gradio, etc.).

Cada subcarpeta dentro de `uis/` debe corresponder a **una interfaz de usuario concreta** (por ejemplo `website`, `backoffice`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar en un único lugar todas las aplicaciones frontend que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) las aplicaciones que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlas.

> _English version: [README.md](./README.md)._

## Interfaces

### `talent-pipeline-tracker`

Herramienta interna de **People & Talent** para gestionar el pipeline de candidaturas de HealthCore.

- **Tecnología**: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- **API**: [Talent Tracker API](https://playground.4geeks.com/tracker/api/v1/docs) (`/records`, no `/applications`)
- **Rutas**:
  - `/applications` — listado, filtros y formulario de alta
  - `/candidates/[id]` — detalle, edición, estado/etapa y notas

**Ejecución:**

```bash
cd uis/talent-pipeline-tracker
npm install
npm run dev
```

#### Checklist de funcionalidades (integración API)

| Área | Requisito | Implementación |
|------|-----------|----------------|
| **Detalle** | Actualizar estado con `PATCH /records/:id` | `StatusStageControls` → `patchRecord()` |
| **Detalle** | Actualizar etapa con `PATCH /records/:id` | `StatusStageControls` → `patchRecord()` |
| **Detalle** | Listar notas con `GET /records/:id/notes` | `fetchNotes()` al cargar el candidato |
| **Detalle** | Añadir nota con `POST /records/:id/notes` | `NoteForm` → `createNote()` |
| **Detalle** | Eliminar nota con `DELETE /records/:id/notes/:note_id` | `NotesSection` → `deleteNote()` |
| **Candidaturas** | Alta con `POST /records` | `ApplicationForm` (create) en `/applications` |
| **Candidaturas** | Edición con `PUT /records/:id` | `ApplicationForm` (edit) en `/candidates/[id]` |
| **Formularios** | Validación de campos requeridos antes de enviar | `ApplicationForm.validateForm()` |
| **Formularios** | Feedback de éxito o error tras cada envío | Mensajes inline + banner en página de detalle |

Documentación detallada en [`talent-pipeline-tracker/README.md`](./talent-pipeline-tracker/README.md).  
Notas de aprendizaje en [`talent-pipeline-tracker/lesson2learn.md`](./talent-pipeline-tracker/lesson2learn.md).
