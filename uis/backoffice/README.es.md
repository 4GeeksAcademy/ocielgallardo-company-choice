# HealthCore Backoffice

Aplicación Next.js interna para empleados de HealthCore.

## Propósito

- Separar el workspace interno del sitio público.
- Mantener el tracker de candidatos (People & Talent).
- Exponer utilidades de negocio de Hito 2 en el dashboard.
- Analizar CSVs de incidentes de pacientes contra la API FastAPI local de HealthCore.

## Secciones actuales

- `/` Dashboard
- `/login` Inicio de sesión (JWT → `localStorage`)
- `/register` Registro (`POST /users` + login automático)
- `/patients` Módulo placeholder
- `/appointments` Módulo placeholder
- `/billing` Módulo placeholder
- `/claims` Módulo placeholder
- `/reports` Módulo placeholder
- `/incidents` Análisis CSV de incidentes (subida, resumen, descarga)
- `/suppliers` Directorio de proveedores (API protegida con Bearer)
- `/applications` Pipeline de candidatos y formulario de alta
- `/candidates/[id]` Detalle, edición, estado/etapa y notas
- `/account/profile` Perfil (email + name/phone/address)

## Incidentes de pacientes (`/incidents`)

Usa la misma pipeline de negocio que el CLI (`services/incidents_analysis/`), expuesta por FastAPI.

### Qué debe estar en marcha

Dos procesos:

1. **API HealthCore** (raíz del repo) — por defecto `http://127.0.0.1:8000`
2. **Este backoffice** — normalmente `http://localhost:3000` (o `3001` si el 3000 está ocupado)

```bash
# Terminal A — desde la raíz del repositorio
python -m pip install fastapi uvicorn python-multipart   # una vez
python -m uvicorn services.app.main:app --reload

# Terminal B — esta app
cd uis/backoffice
npm install   # una vez
npm run dev
```

Abre la URL que imprima Next (por ejemplo `http://localhost:3001/incidents` si el puerto 3000 está ocupado).

Swagger de la API: `http://127.0.0.1:8000/docs`

### Cómo analizar un CSV

1. En el menú, entra en **Incidents**.
2. Arrastra o selecciona un `.csv` (muestra: `data/raw/incidents-healthcore.csv` en la raíz del repo).
3. Pulsa **Analyze CSV**.
4. Revisa totales, desglose de inválidos por regla, categoría, estado y satisfacción.
5. Pulsa **Download results CSV** para bajar el último análisis (`GET /api/incidents/results/export`).

Con el CSV oficial se espera: **100** total / **94** válidos / **6** inválidos; media de satisfacción **3.58**.

### URL base de la API

Cliente: `lib/services/healthcoreApi.ts`

- Por defecto: `http://127.0.0.1:8000`
- Override: variable `NEXT_PUBLIC_HEALTHCORE_API_URL` (reinicia `npm run dev` tras cambiarla)

CORS en la API permite `localhost` / `127.0.0.1` en puertos **3000** y **3001**. Si Next usa otro puerto, añade ese origen en `services/app/main.py`.

### Auth frontend (AUTH-02 — completo)

- `/login` y `/register`: JWT en `localStorage` (`healthcore_access_token`); redirect a `/`.
- `healthcoreClient.ts`: Bearer en llamadas; **401** → clear + `/login`.
- `AppChrome`: sin shell en auth; sin token en el resto → `/login`.
- `/account/profile`: `GET /auth/me` + `PUT /profiles/me` (email solo lectura).
- Shell: enlace Profile + **Cerrar sesión** (`clearSessionAndRedirectToLogin`).
- Website público sin auth. Runtime `data/process/auth/auth.json` en `.gitignore`.

### Archivos de auth

| Ruta | Rol |
| --- | --- |
| `app/login/page.tsx` | Inicio de sesión |
| `app/register/page.tsx` | Registro |
| `app/account/profile/page.tsx` | Perfil |
| `components/forms/LoginForm.tsx` | Login → token → `/` |
| `components/forms/RegisterForm.tsx` | Registro + confirmación de contraseña |
| `components/forms/ProfileForm.tsx` | Editar name/phone/address |
| `components/layout/AppChrome.tsx` | Guard de rutas + shell |
| `components/layout/BackofficeShell.tsx` | Nav + logout |
| `lib/services/healthcoreClient.ts` | Token, Bearer, 401 |
| `lib/services/authApi.ts` | login, register, me, updateMyProfile |
| `types/auth.ts` | Tipos auth |

### Archivos relacionados

| Ruta | Rol |
| --- | --- |
| `app/incidents/page.tsx` | Página: subir → analizar → resumen → descargar |
| `components/incidents/IncidentCsvUpload.tsx` | Selector + drag and drop |
| `components/incidents/IncidentAnalysisSummary.tsx` | Métricas alineadas al CONTEXT |
| `lib/services/healthcoreApi.ts` | `POST /api/incidents/analyze`, `GET .../results/export` |
| `types/incidents.ts` | Tipos del resumen JSON |

Las reglas de negocio viven en `services/incidents_analysis/` (sin duplicarlas aquí). El Tracker sigue usando `lib/services/client.ts` (API 4Geeks).

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

Para análisis de incidentes, arranca también la API (ver [Incidentes de pacientes](#incidentes-de-pacientes-incidents)).

## Build

```bash
npm run build
npm start
```

## Notas

- Candidatos: API Talent Tracker de 4Geeks (`/records`).
- Incidentes: FastAPI local HealthCore (`services/app`).
- Auth HealthCore: login/register en este backoffice; el website público no usa JWT.
- `next.config.ts` permite imports externos a utilidades de Hito 2.

> English version: [README.md](./README.md).
