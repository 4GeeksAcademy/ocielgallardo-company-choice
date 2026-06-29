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
Notas de aprendizaje en [`lesson2learn.md`](./lesson2learn.md).


## Actualización — junio 2026

### Resumen

Implementación completa del **Talent Pipeline Tracker** para **HealthCore** (área **Personas y Fuerza Laboral**, Diane Foster). La app consume la [Talent Tracker API](https://playground.4geeks.com/tracker/api/v1/docs) y permite gestionar el pipeline de candidaturas clínicas en las 12 sedes de HealthCore.

### Rutas

| Ruta | Descripción |
|------|-------------|
| `/applications` | Listado, filtros, búsqueda y alta de candidaturas |
| `/candidates/[id]` | Detalle, edición, estado/etapa, notas y enlace al CV |

### Integración con la API

| Operación | Endpoint | Dónde |
|-----------|----------|-------|
| Listar candidaturas | `GET /records` | `/applications` |
| Ver detalle | `GET /records/:id` | `/candidates/[id]` |
| Registrar candidatura | `POST /records` | Formulario en `/applications` |
| Editar datos | `PUT /records/:id` | Formulario en `/candidates/[id]` |
| Cambiar estado o etapa | `PATCH /records/:id` | Controles en el detalle |
| Listar notas | `GET /records/:id/notes` | Sección de notas |
| Añadir nota | `POST /records/:id/notes` | Formulario de notas |
| Eliminar nota | `DELETE /records/:id/notes/:note_id` | Botón en cada nota |

### Funcionalidades implementadas

- Listado con badges de estado y etapa, filtros por URL y búsqueda por nombre/email en cliente.
- Formularios de alta y edición con validación de campos requeridos y feedback de éxito/error.
- Controles de pipeline con actualización optimista (sin recargar la página).
- CRUD de notas internas con validación y manejo de errores al crear o eliminar.
- Enlace al CV cuando `cv_url` está disponible.
- Estados async en la UI: **cargando**, **éxito** y **error** (con reintentar) en listado, detalle y notas.
- Tras `POST`, `PUT` y `PATCH`, la interfaz se actualiza en cliente sin `location.reload()`.

### Arquitectura

- **Stack:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4.
- **Estado:** hooks de React (`useState`, `useEffect`, `useCallback`) — sin Redux, Zustand ni Jotai.
- **Estructura:** `components/`, `hooks/`, `types/`, `lib/services/`, `lib/constants/`, `lib/utils/`.
- **Servicios:** capa `lib/services/` con `async/await` centralizado (`client`, `records`, `notes`).
- **Hooks:** `useRecords`, `useCandidateDetail`, `useDebouncedValue`.
- **Tipos:** `types/application.ts` (API) y `types/async.ts` (estados de carga).

### Contexto de empresa

La interfaz está adaptada a **HealthCore** y al equipo de **People & Talent** (Diane Foster). Los campos de la API siguen los nombres del backend (`full_name`, `status`, `stage`, etc.); las etiquetas visibles están en español y alineadas con el pipeline de RR.HH.
