# Lecciones aprendidas — Talent Pipeline Tracker

Qué deberías estudiar para construir esta app por tu cuenta, por qué importa cada decisión y qué implementamos en esta sesión.

---

## Qué deberías aprender

### 1. React y Next.js (App Router)

- **Componentes cliente** (`"use client"`) para interactividad: formularios, filtros y llamadas a la API desde el navegador.
- **Enrutado basado en archivos**: `app/applications/page.tsx`, `app/candidates/[id]/page.tsx`.
- **`useSearchParams`** para filtros en la URL (enlaces compartibles, compatible con atrás/adelante del navegador).
- **`Suspense`** al usar `useSearchParams` en componentes cliente.

### 2. TypeScript para contratos de API

- Definir tipos (`Application`, `Note`, `RecordCreateInput`) que reflejen la respuesta de la API.
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

### 4. Fetch API y una capa cliente delgada

- Centralizar `fetch` en `lib/api/client.ts` (URL base, cabeceras, manejo de errores).
- Separar por dominio: `records.ts`, `notes.ts`.
- Lanzar errores tipados (`ApiError`) para que la UI muestre mensajes útiles.

### 5. Validación de formularios y feedback de UX

- Validar **antes** de llamar a la API (campos obligatorios, formato de email, experiencia numérica).
- Mostrar errores por campo (`aria-invalid`, `role="alert"`).
- Mostrar éxito o error tras el envío (`aria-live="polite"`).
- Cuando hay navegación tras el éxito (crear → página de detalle), pasar el feedback con un query param (`?created=1`) en lugar de perder el mensaje.

### 6. Patrones de gestión de estado

- **Actualizaciones optimistas** para estado/etapa: actualizar la UI al instante y revertir si falla.
- **Estado local** en listas tras mutaciones (añadir nota al inicio, filtrar tras eliminar).
- Estados de **carga / error / vacío** en cada vista asíncrona.

### 7. Tailwind CSS

- Clases utilitarias para layout, espaciado y contraste de color accesible.
- Grids responsivos (`sm:grid-cols-2`) para formularios y paneles de detalle.

### 8. Fundamentos de accesibilidad

- Etiquetas vinculadas a inputs (`htmlFor` / `id`).
- Regiones en vivo para feedback dinámico.
- HTML semántico (`article`, `section`, `role="alert"`).

---

## Por qué construirlo así

### Capa API separada (`lib/api/`)

**Por qué:** Un solo lugar para cambiar la URL base, cabeceras de autenticación o el parseo de errores. Los componentes se centran en la UI.

### Ruta de detalle dedicada (`/candidates/[id]`)

**Por qué:** Enlaces profundos (compartir la URL de un candidato), separación clara entre el espacio de listado y el de detalle, y un lugar natural para cargar `GET /records/:id` y las notas en paralelo.

### Filtrado en el cliente

**Por qué:** La API devuelve hasta 100 registros; filtrar por estado, etapa y búsqueda en el navegador evita viajes extra al servidor y mantiene la UI instantánea. Con más datos, moverías los filtros a query params en la API.

### PATCH para el pipeline, PUT para editar el perfil

**Por qué:** Respeta la intención REST y reduce el riesgo de sobrescribir campos no relacionados cuando solo cambia el estado o la etapa.

### Validación en el componente del formulario

**Por qué:** Feedback inmediato sin llamada de red. La API sigue validando en servidor; la capa cliente mejora la UX y reduce peticiones incorrectas.

### Re-lanzar errores desde los handlers padre

**Por qué:** `ApplicationForm` y `NoteForm` capturan errores para mostrar mensajes inline. Si el padre los traga, el formulario nunca sabe que la petición falló.

### Mensaje flash tras redirigir al crear

**Por qué:** Tras un `POST /records` exitoso navegamos al detalle. Mostrar el éxito ahí (`?created=1` → banner) es más fiable que un mensaje en una página que se desmonta.

---

## Lo que hicimos en esta sesión

### Verificación

Confirmamos que la app ya cubría el checklist completo:

- Controles de estado y etapa → `PATCH /records/:id`
- Listar, crear y eliminar notas → `GET`, `POST`, `DELETE` en `/records/:id/notes`
- Formulario de alta → `POST /records` en `/applications`
- Formulario de edición → `PUT /records/:id` en `/candidates/[id]`
- Validación de campos obligatorios en `ApplicationForm`

### Mejoras añadidas

1. **Feedback de éxito al crear** — redirección a `/candidates/:id?created=1` y banner de éxito en la página de detalle.
2. **Feedback de error/éxito al editar** — banner en el detalle; errores re-lanzados para que el formulario también muestre mensaje mientras sigue abierto.
3. **Errores al borrar notas** — `NotesSection` muestra una alerta si falla el `DELETE`.
4. **Propagación de errores** — `handleCreate`, `handleAddNote` y `handleDeleteNote` re-lanzan para que los formularios hijos gestionen los fallos correctamente.
5. **Documentación** — actualización de `uis/README.md`, `uis/README.es.md` y este archivo.

### Archivos clave

| Archivo | Rol |
|---------|-----|
| `components/ApplicationsWorkspace.tsx` | Listado, filtros, formulario de alta |
| `components/candidates/CandidateDetailWorkspace.tsx` | Orquestación de la página de detalle |
| `components/detail/ApplicationDetailPanel.tsx` | Estado/etapa, notas, enlace al CV |
| `components/forms/ApplicationForm.tsx` | Alta/edición con validación |
| `components/forms/NoteForm.tsx` | Añadir nota con validación |
| `lib/api/records.ts` | CRUD + PATCH de registros |
| `lib/api/notes.ts` | CRUD de notas |

---

## Ruta de práctica sugerida

1. Lee la [documentación de la Talent Tracker API](https://playground.4geeks.com/tracker/api/v1/docs) y prueba los endpoints con `curl` o Postman.
2. Construye una página mínima que solo liste registros (`GET /records`).
3. Añade una mutación cada vez (crear → cambiar estado con patch → notas).
4. Añade validación y estados de carga al final — son más fáciles cuando el flujo feliz ya funciona.
5. Compara tu enfoque con este código y anota qué simplificarías o ampliarías (paginación, autenticación, tests).
