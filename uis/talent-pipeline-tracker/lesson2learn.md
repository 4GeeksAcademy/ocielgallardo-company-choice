# Lecciones aprendidas — Talent Pipeline Tracker

Qué deberías estudiar para construir esta app por tu cuenta, por qué importa cada decisión y qué implementamos en este proyecto.

---

## Qué deberías aprender

### 1. React y Next.js (App Router)

- **Componentes cliente** (`"use client"`) para interactividad: formularios, filtros y llamadas a la API desde el navegador.
- **Enrutado basado en archivos**: `app/applications/page.tsx`, `app/candidates/[id]/page.tsx`.
- **`useSearchParams`** para filtros en la URL (enlaces compartibles, compatible con atrás/adelante del navegador).
- **`Suspense`** al usar `useSearchParams` en componentes cliente.
- **Sin librerías de estado global** (Redux, Zustand, Jotai): `useState`, `useEffect` y `useCallback` en componentes y hooks personalizados son suficientes para este hito.

### 2. TypeScript para contratos de API

- Definir tipos en `/types` (`Application`, `Note`, `RecordCreateInput`, `AsyncState`) que reflejen la respuesta de la API.
- Detectar inconsistencias en tiempo de compilación en lugar de depurar en producción.

### 3. Semántica HTTP y REST

| Método | Cuándo usarlo | Ejemplo en esta app |
|--------|---------------|---------------------|
| GET | Leer datos | Listar registros, obtener uno, listar notas |
| POST | Crear un recurso | Nueva candidatura, nueva nota |
| PUT | Reemplazar el recurso completo | Editar los datos del candidato |
| PATCH | Actualización parcial | Cambiar solo `status` o `stage` |
| DELETE | Eliminar un recurso | Borrar una nota |

Entender **PUT vs PATCH** es esencial: editar un formulario envía todos los campos (PUT); cambiar un desplegable envía solo lo que cambió (PATCH).

Todas las llamadas usan **`async/await`** dentro de servicios (`lib/services/`) y hooks (`hooks/`).

### 4. Estado asíncrono en la UI (cargando · éxito · error)

Cada operación de **lectura** debe exponer tres estados en la interfaz:

| Estado | Qué muestra la UI |
|--------|-------------------|
| **Cargando** | Skeletons o indicador de carga |
| **Éxito** | Datos renderizados (o estado vacío si no hay resultados) |
| **Error** | Mensaje claro + botón de reintentar cuando aplique |

Implementación:

- `hooks/useRecords.ts` — listado en `/applications`
- `hooks/useCandidateDetail.ts` — candidato y notas con estados **independientes**
- `types/async.ts` — tipo `AsyncStatus` (`loading` | `success` | `error`)

Tras **PATCH, PUT o POST**, la UI se actualiza **sin recargar la página**:

- Estado/etapa: actualización optimista + respuesta del servidor
- Edición: `setApplication(refreshed)` tras `PUT`
- Notas: prepend en lista local tras `POST`; filtro tras `DELETE`
- Alta: navegación cliente a `/candidates/:id?created=1`

### 5. Estructura de carpetas

```
talent-pipeline-tracker/
├── app/                    # Rutas Next.js (App Router)
├── components/             # UI por dominio (applications, detail, forms, layout, ui)
├── hooks/                  # Lógica reutilizable (useRecords, useCandidateDetail, useDebouncedValue)
├── types/                  # Tipos TypeScript (application, async)
└── lib/
    ├── services/           # Capa API (client, records, notes) — async/await + fetch
    ├── constants/          # Etiquetas de dominio (estados, etapas)
    └── utils/              # Helpers puros (filtros)
```

**Por qué así:** separa presentación, estado, tipos y acceso a datos. Los componentes no llaman a `fetch` directamente.

### 6. Contexto de empresa (HealthCore)

La interfaz debe sentirse como herramienta interna del equipo de **People & Talent** de **HealthCore**, no como una app genérica:

- Marca: **HealthCore** en cabecera
- Área: **Personas y Fuerza Laboral** — responsable **Diane Foster** (`CONTEXT.md`)
- Copy orientado a contratación clínica en **12 sedes** (EE.UU. y Reino Unido)
- Los **nombres de campos de la API** (`full_name`, `status`, `stage`, etc.) se mantienen tal como define el backend del tracker
- Las **etiquetas visibles** están en español y alineadas con el pipeline de RR.HH. (`Recibida`, `Entrevista técnica`, etc.)

### 7. Validación de formularios y feedback de UX

- Validar **antes** de llamar a la API (campos obligatorios, formato de email, experiencia numérica).
- Mostrar errores por campo (`aria-invalid`, `role="alert"`).
- Mostrar éxito o error tras el envío (`aria-live="polite"`).
- Cuando hay navegación tras el éxito (crear → detalle), pasar el feedback con `?created=1`.

### 8. Tailwind CSS y accesibilidad

- Clases utilitarias para layout, espaciado y contraste accesible (design system HealthCore).
- Etiquetas vinculadas a inputs, regiones en vivo y HTML semántico.

---

## Por qué construirlo así

### Capa de servicios (`lib/services/`)

**Por qué:** Un solo lugar para `async/await`, URL base, cabeceras y errores tipados (`ApiError`). Los componentes y hooks solo orquestan.

### Hooks personalizados en lugar de Redux

**Por qué:** El alcance del hito es acotado (listado + detalle + formularios). Extraer `useRecords` y `useCandidateDetail` mantiene los tres estados async visibles y testeables sin añadir dependencias.

### Estados async separados para candidato y notas

**Por qué:** Si falla `GET /notes` pero el candidato cargó bien, el detalle sigue visible y solo la sección de notas muestra error + reintentar.

### PATCH para el pipeline, PUT para editar el perfil

**Por qué:** Respeta REST y evita sobrescribir campos no relacionados.

### Re-lanzar errores desde handlers padre

**Por qué:** `ApplicationForm` y `NoteForm` capturan errores para mensajes inline. Si el padre los traga, el formulario no sabe que falló.

### Sin recarga de página tras mutaciones

**Por qué:** Mejor UX, menos ancho de banda y coherencia con una SPA moderna. Next.js navega entre rutas en cliente; el estado local refleja los cambios al instante.

---

## Lo que hicimos en esta sesión

### Verificación del hito

| Requisito | Estado |
|-----------|--------|
| Todas las llamadas API con `async/await` | ✅ `lib/services/` |
| Tres estados UI en cada GET (cargando, éxito, error) | ✅ Listado + detalle + notas |
| UI actualizada tras PATCH/PUT/POST sin reload | ✅ Estado local + navegación cliente |
| Estructura `/components`, `/hooks`, `/types`, `/lib/services` | ✅ Reorganizado |
| Tipos TS para todas las estructuras de la API | ✅ `types/application.ts` |
| Contexto HealthCore / Diane Foster / People & Talent | ✅ Cabecera y copy |
| Solo Next.js + React + TS, sin Redux/Zustand | ✅ `package.json` |

### Cambios implementados

1. **Reorganización** — `lib/api` → `lib/services`; `lib/types` → `types/`.
2. **Hooks** — `useRecords`, `useCandidateDetail`, `useDebouncedValue`.
3. **Estados async** — `ApplicationList` muestra error con reintentar (antes confundía error con “sin resultados”). `NotesSection` con error independiente.
4. **Branding** — Diane Foster en cabecera; copy de contratación clínica en `/applications`.
5. **Documentación** — este archivo actualizado.

### Archivos clave

| Archivo | Rol |
|---------|-----|
| `hooks/useRecords.ts` | GET listado con estados async |
| `hooks/useCandidateDetail.ts` | GET candidato + notas con estados independientes |
| `lib/services/records.ts` | CRUD + PATCH (async/await) |
| `lib/services/notes.ts` | CRUD de notas (async/await) |
| `types/application.ts` | Tipos de la API |
| `types/async.ts` | `AsyncStatus` reutilizable |
| `components/ApplicationsWorkspace.tsx` | Pipeline + alta |
| `components/candidates/CandidateDetailWorkspace.tsx` | Detalle + mutaciones |

---

## Ruta de práctica sugerida

1. Lee la [documentación de la Talent Tracker API](https://playground.4geeks.com/tracker/api/v1/docs) y prueba endpoints con `curl` o Postman.
2. Crea `types/` y `lib/services/client.ts` antes de cualquier componente.
3. Implementa un hook con los tres estados async para el listado.
4. Añade mutaciones una a una; verifica que la UI se actualiza sin `location.reload()`.
5. Revisa `CONTEXT.md` y adapta textos de la UI a tu empresa antes de pulir estilos.
