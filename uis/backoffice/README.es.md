# HealthCore Backoffice

Aplicación Next.js interna para empleados de HealthCore.

## Propósito

- Separar el workspace interno del sitio público.
- Mantener el tracker de candidatos (People & Talent).
- Exponer utilidades de negocio de Hito 2 en el dashboard.
- Analizar y gestionar incidencias contra la API FastAPI local de HealthCore (registro, listado, resumen + análisis CSV).

## Secciones actuales

- `/` Dashboard
- `/login` Inicio de sesión (JWT → `localStorage`)
- `/register` Registro (`POST /users` + login automático)
- `/forgot-password` Solicitar email de restablecimiento
- `/reset-password` Nueva contraseña desde el token del email (`?token=`)
- `/patients` Módulo placeholder
- `/appointments` Módulo placeholder
- `/billing` Módulo placeholder
- `/claims` Módulo placeholder
- `/reports` Módulo placeholder
- `/incidents` Gestor: listado (filtros + cambio de estado)
- `/incidents/new` Registrar incidencia (aviso PHI en description)
- `/incidents/summary` Métricas agregadas por status/categoría/origen/sede
- `/incidents/analyze` Análisis CSV de incidentes (subida, resumen, descarga)
- `/suppliers` Directorio de proveedores (API protegida con Bearer)
- `/inventory/products` Suministros médicos con stock actual (badges de nivel)
- `/inventory/orders/inbound` Registrar entrega de proveedor
- `/inventory/orders/outbound` Registrar consumo clínico (stock reactivo + aviso si excede)
- `/inventory/orders` Historial de órdenes (solo lectura)
- `/applications` Pipeline de candidatos y formulario de alta
- `/candidates/[id]` Detalle, edición, estado/etapa y notas
- `/account/profile` Perfil (email + name/phone/address)
- `/account/change-password` Cambio de contraseña con sesión

## Inventario (`/inventory`)

Cuatro vistas autenticadas contra `GET/POST /inventory/*` (Bearer). Contrato: `docs/inventory/CONTEXT-HealthCore.es.md`. Cliente: `lib/services/inventoryApi.ts`.

| Ruta | Rol |
| --- | --- |
| `/inventory/products` | Listado de suministros con `current_stock` e indicadores visuales (crítico &lt; 5, bajo &lt; 15) |
| `/inventory/orders/inbound` | Formulario de entrega (`POST /inventory/orders/inbound`) |
| `/inventory/orders/outbound` | Formulario de consumo; muestra stock del producto seleccionado; aviso en cliente si la cantidad supera el stock; `HTTP 400` inline en cantidad |
| `/inventory/orders` | Historial de entregas y consumos (solo lectura) |

Nav: Suministros, Registrar entrega, Registrar consumo, Historial de órdenes.

## Gestor de incidencias (`/incidents`)

Registro y seguimiento centralizado para las clínicas HealthCore. Contrato: `docs/incident-manager/CONTEXT-HealthCore.es.md`. Etiquetas de UI en **inglés**.

### Rutas

| Ruta | Rol |
| --- | --- |
| `/incidents` | Listado + filtros (`status`, `origin`, `branch`) + transiciones de estado con rollback si falla |
| `/incidents/new` | Formulario de alta; `branch` siempre obligatorio; se destaca si `origin === branch`; aviso PHI antes de description |
| `/incidents/summary` | Totales de `GET /api/incidents/summary` (carga/error aislados) |
| `/incidents/analyze` | UI del analizador CSV (misma pipeline que el CLI) |

### Qué debe estar en marcha

1. **API HealthCore** (raíz del repo) — por defecto `http://127.0.0.1:8000`
2. **Este backoffice** — normalmente `http://localhost:3000` (o `3001`)

```bash
# Terminal A — desde la raíz del repositorio
PYTHONPATH=packages/shared uv run uvicorn services.app.main:app --reload
# seed histórico opcional
PYTHONPATH=packages/shared uv run python scripts/seed_incidents.py

# Terminal B — esta app
cd uis/backoffice
npm install   # una vez
npm run dev
```

Inicia sesión primero (el gestor exige Bearer). Swagger: `http://127.0.0.1:8000/docs`

### Archivos del gestor

| Ruta | Rol |
| --- | --- |
| `app/incidents/page.tsx` | Listado |
| `app/incidents/new/page.tsx` | Alta |
| `app/incidents/summary/page.tsx` | Resumen |
| `components/incidents/IncidentListPanel.tsx` | Filtros, tabla, status |
| `components/incidents/IncidentCreateForm.tsx` | Formulario + aviso PHI |
| `components/incidents/IncidentSummaryPanel.tsx` | Paneles de métricas |
| `lib/services/incidentsManagerApi.ts` | Cliente API + errores amigables |
| `types/incidentManager.ts` | Tipos, opciones y etiquetas |

## Análisis CSV de incidentes (`/incidents/analyze`)

Usa la misma pipeline que el CLI (`services/incidents_analysis/`), expuesta por FastAPI. Las reglas de validación viven en `packages/shared/healthcore_shared`.

### Cómo analizar un CSV

1. Abre **CSV analyzer** desde Incidents (o `/incidents/analyze`).
2. Arrastra o selecciona un `.csv` (muestra: `data/raw/incidents-healthcore.csv`).
3. Pulsa **Analyze CSV**.
4. Revisa totales, inválidos por regla, categoría, estado y satisfacción.
5. Pulsa **Download results CSV** (`GET /api/incidents/results/export`).

Con el CSV oficial: **100** total / **94** válidos / **6** inválidos; media de satisfacción **3.58**.

### URL base de la API

Clientes: `lib/services/healthcoreClient.ts`, `incidentsManagerApi.ts`, `healthcoreApi.ts`

- Por defecto: `http://127.0.0.1:8000`
- Override: variable `NEXT_PUBLIC_HEALTHCORE_API_URL` (reinicia `npm run dev` tras cambiarla)

CORS en la API permite `localhost` / `127.0.0.1` en puertos **3000** y **3001**. Si Next usa otro puerto, añade ese origen en `services/app/main.py`.

### Auth frontend (AUTH-02 / AUTH-03 — completo)

- `/login` y `/register`: JWT en `localStorage` (`healthcore_access_token`); redirect a `/`.
- Login incluye “¿Olvidaste tu contraseña?” → `/forgot-password`.
- `/forgot-password`: tras enviar, siempre muestra confirmación genérica (anti-enumeración). Llama `POST /auth/forgot-password` con `auth: false`.
- `/reset-password?token=...`: nueva contraseña + confirmación → `POST /auth/reset-password`; éxito → `/login?reset=success`.
- `/account/change-password`: actual + nueva + confirmación → `POST /auth/change-password` (Bearer).
- `healthcoreClient.ts`: Bearer en llamadas; **401** → clear + `/login` (no aplica en páginas auth, incluidas forgot/reset).
- `AppChrome`: sin shell en `/login`, `/register`, `/forgot-password`, `/reset-password`; sin token en el resto → `/login`.
- `/account/profile`: `GET /auth/me` + `PUT /profiles/me` (email solo lectura).
- Shell: Profile + Change password + **Cerrar sesión** (`clearSessionAndRedirectToLogin`).
- Website público sin auth. Runtime `data/process/auth/auth.json` en `.gitignore`.
- El email lo envía la **API** (Resend). Configura el `.env` de la raíz (`RESEND_API_KEY`, `EMAIL_FROM`, `FRONTEND_BASE_URL`); nunca uses `NEXT_PUBLIC_*` para keys de correo.

### Archivos de auth

| Ruta | Rol |
| --- | --- |
| `app/login/page.tsx` | Inicio de sesión (+ banner post-reset) |
| `app/register/page.tsx` | Registro |
| `app/forgot-password/page.tsx` | Olvidé mi contraseña |
| `app/reset-password/page.tsx` | Restablecer (Suspense + token reader) |
| `app/account/profile/page.tsx` | Perfil |
| `app/account/change-password/page.tsx` | Cambiar contraseña |
| `components/forms/LoginForm.tsx` | Login → token → `/` |
| `components/forms/RegisterForm.tsx` | Registro + confirmación de contraseña |
| `components/forms/ForgotPasswordForm.tsx` | Solicitar email de reset |
| `components/forms/ResetPasswordForm.tsx` | Nueva contraseña con token |
| `components/forms/ChangePasswordForm.tsx` | Cambio autenticado |
| `components/forms/ProfileForm.tsx` | Editar name/phone/address |
| `components/layout/AppChrome.tsx` | Guard de rutas + shell |
| `components/layout/BackofficeShell.tsx` | Nav + logout |
| `lib/services/healthcoreClient.ts` | Token, Bearer, 401 |
| `lib/services/authApi.ts` | login, register, me, profile, forgot/reset/change |
| `types/auth.ts` | Tipos auth |

### Archivos del analizador CSV

| Ruta | Rol |
| --- | --- |
| `app/incidents/analyze/page.tsx` | Subir → analizar → resumen → descargar |
| `components/incidents/IncidentCsvUpload.tsx` | Selector + drag and drop |
| `components/incidents/IncidentAnalysisSummary.tsx` | Métricas alineadas al CONTEXT |
| `lib/services/healthcoreApi.ts` | `POST /api/incidents/analyze`, `GET .../results/export` |
| `types/incidents.ts` | Tipos del resumen JSON |

Las reglas del gestor viven en `packages/shared/healthcore_shared` y `services/app/domain/incident_manager_service.py`. El Tracker sigue usando `lib/services/client.ts` (API 4Geeks).

## Integración Hito 2

El dashboard importa utilidades desde la raíz `src/`:

- `src/utils/collections.ts`
- `src/utils/search.ts`
- `src/utils/transformations.ts`
- `src/utils/validations.ts`
- `src/types/models.ts`

Una sola fuente de lógica, sin duplicación.

## Stack

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS 4

## Arranque

```bash
cd uis/backoffice
npm install
npm run dev
```

Para el gestor o el análisis CSV, arranca también la API (ver [Gestor de incidencias](#gestor-de-incidencias-incidents)).

## Build

```bash
npm run build
npm start
```

## Notas

- Candidatos: API Talent Tracker de 4Geeks (`/records`).
- Gestor de incidencias y análisis CSV: FastAPI local HealthCore (`services/app`).
- Auth HealthCore: login/register/forgot/reset/change-password en este backoffice; el website público no usa JWT.
- `next.config.ts` permite imports externos a utilidades de Hito 2.

> English version: [README.md](./README.md).
