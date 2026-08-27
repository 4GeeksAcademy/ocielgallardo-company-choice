# services

Esta carpeta define los límites de servicios backend dentro de la arquitectura monorepo.

## Propósito

- Separar backend de las aplicaciones UI.
- Preparar APIs futuras como unidades independientes y escalables.
- Dejar explícita la responsabilidad por dominio.

## Estructura actual (placeholders)

- `_template-service/` plantilla base para nuevos servicios.
- `gateway/` responsabilidades transversales en el borde.
- `clinical-operations/` servicios de citas y flujos clínicos.
- `revenue-cycle/` servicios de facturación y reclamos.
- `compliance/` servicios de cumplimiento y auditoría.

## Implementado (Python, reutilizable por CLI / API)

- `incidents_analysis/` — análisis CSV de incidentes de pacientes HealthCore (`models`, `csv_reader`, `validator` reexporta `healthcore_shared`, `analyzer`, `exporter`). Lo consumen `scripts/analyze.py` y la capa de dominio de la API.
- `app/` — aplicación FastAPI (`services/app/main.py`) en capas:
	- `core/` — TinyDB + motor SQLModel (`database.py`), seeds, helpers JWT/password (`security.py`), `deps.py` (`get_current_user`)
	- `models/` — Pydantic (`supplier`, `user`, `profile`) y ORM de inventario SQLModel (`inventory.py`)
	- `schemas.py` — request/response Pydantic de inventario (separado del ORM)
	- `domain/` — orquestación de negocio (`supplier_service`, `incident_service`, `user_service`, `profile_service`, `inventory_service`)
	- `routers/` — solo HTTP:
		- `incidents.py` → `POST /api/incidents/analyze`, `GET /api/incidents/results/export`
		- `suppliers.py` → CRUD + filtros + rate/status del directorio de proveedores (**requiere Bearer**)
		- `users.py` → CRUD de credenciales (`POST` público; `GET/PUT/DELETE` requieren Bearer; PUT/DELETE dueño o admin)
		- `auth.py` → `POST /auth/login`, `GET /auth/me` (JWT)
		- `profiles.py` → `GET/PUT /profiles/me` (JWT)
		- `inventory.py` → `/inventory/*` suministros médicos + entregas/consumos (**requiere Bearer**)

Notas de auth (AUTH-01, rama `feature/auth`):
  - `core/` — TinyDB (`database.py`: suppliers, auth, **incidents**), seed de proveedores (`seed.py`), helpers JWT/password (`security.py`), `deps.py` (`get_current_user`)
  - `models/` — modelos Pydantic (`supplier`, `user`, `profile`, `incident`)
  - `domain/` — orquestación (`supplier_service`, `incident_service` analyze CSV, `incident_manager_service` CRUD/summary, `user_service`, `profile_service`, `password_reset_service`)
  - `routers/` — solo HTTP:
    - `incidents.py` → analyze/export **y** gestor:
      - `POST /api/incidents/analyze`, `GET /api/incidents/results/export` (públicos)
      - `POST /api/incidents`, `GET /api/incidents`, `GET /api/incidents/summary`, `GET /api/incidents/{id}`, `PATCH /api/incidents/{id}/status` (**requieren Bearer**)
    - `suppliers.py` → CRUD + filtros + rate/status del directorio de proveedores (**requiere Bearer**)
    - `users.py` → CRUD de credenciales (`POST` público; `GET/PUT/DELETE` requieren Bearer; PUT/DELETE dueño o admin)
    - `auth.py` → `POST /auth/login`, `GET /auth/me`, `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/change-password`
    - `profiles.py` → `GET/PUT /profiles/me` (JWT)

Validación/constantes compartidas: `packages/shared/healthcore_shared` (ver `packages/shared/README.md`). Seed histórico: `PYTHONPATH=packages/shared uv run python scripts/seed_incidents.py`.

Notas de auth (AUTH-01 / AUTH-03):

- Contraseñas con `passlib` + `bcrypt` (fijar `bcrypt==4.0.1` por compatibilidad con passlib).
- JWT con `python-jose`; `SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` en el `.env` de la raíz (ver `.env.example`).
- User y Profile solo en TinyDB (no tablas de usuario en PostgreSQL/Supabase). Tokens de reset en tabla TinyDB `password_reset_tokens` (hash, TTL corto, un solo uso).
- Todas las rutas `/suppliers` y las de `/users` no públicas requieren `Authorization: Bearer <token>` (401 sin él).
- Recuperación de contraseña (AUTH-03, rama `feature/password-reset`):
  - `POST /auth/forgot-password` siempre 200 (anti-enumeración); email vía Resend si el usuario existe.
  - `POST /auth/reset-password` valida token/expiración/uso único; actualiza hash; invalida el token.
  - `POST /auth/change-password` requiere Bearer; verifica la contraseña actual primero.
  - Env: `RESEND_API_KEY`, `EMAIL_FROM` (usar `onboarding@resend.dev` en onboarding Resend), `FRONTEND_BASE_URL`, `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`, opcional `EMAIL_SSL_VERIFY` (workaround TLS en Windows local). Nunca commitear keys reales.
- Consumidor frontend (AUTH-02/03): el backoffice guarda el JWT en `localStorage` y envía Bearer vía `uis/backoffice/lib/services/healthcoreClient.ts` (`/login`, `/register`, flujos forgot/reset/change-password).

Notas de inventario (Hito 5, rama `feature/inventory`):

- Doble DB: TinyDB (auth) + Supabase PostgreSQL con SQLModel.
- Conexión Supabase (`.env` en la raíz del repo, ver `.env.example`):
  - Recomendado: variables `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, `SUPABASE_DB_NAME`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD` (Transaction / Shared pooler).
  - Opcional: `DATABASE_URL` completa (la contraseña debe ir percent-encoded si tiene caracteres especiales).
  - `services/app/core/database.py` construye la URI con `quote_plus` cuando usas variables sueltas; no commitees secretos.
- Entidades: `MedicalSupply`, `SupplyDelivery`, `SupplyConsumption`. Stock calculado, nunca almacenado.
- Contexto: `docs/inventory/CONTEXT-HealthCore.es.md`

Desde la raíz del repo:

```bash
PYTHONPATH=packages/shared uv run python -m uvicorn services.app.main:app --reload
uv run python -m services.app.core.seed
uv run python -m services.app.core.inventory_seed
PYTHONPATH=packages/shared uv run python scripts/seed_incidents.py
```

### Rutas de datos en runtime usadas por `services/app`

- `data/process/results.csv` — último resumen de análisis CSV exportado.
- `data/process/suppliers/suppliers.json` — archivo TinyDB del directorio de proveedores.
- `data/process/auth/auth.json` — TinyDB de users, profiles y tokens de reset (en `.gitignore`).
- `data/process/incidents/incidents.json` — TinyDB del gestor de incidencias (en `.gitignore`).

## Estado

La lógica de análisis de incidentes vive en `incidents_analysis/` y se reutiliza vía `app/domain/incident_service`. AUTH-01 aplica JWT a users (salvo registro) y a todas las rutas de suppliers; inventario exige Bearer. Incidents siguen públicas por ahora. Los demás dominios (`gateway`, `clinical-operations`, `revenue-cycle`, `compliance`) siguen como placeholders.
La lógica de análisis CSV vive en `incidents_analysis/` (reglas vía `healthcore_shared`) y se reutiliza con `app/domain/incident_service`. El **gestor de incidencias** persiste en TinyDB y expone CRUD/summary/status autenticados (`incident_manager_service`). AUTH-01 aplica JWT a users (salvo registro), suppliers y rutas del gestor; analyze/export CSV siguen públicos. AUTH-03 añade forgot/reset/change-password con Resend. El backoffice (AUTH-02/03) adjunta Bearer desde `localStorage` tras `/login` o `/register` y expone la UI de recuperación. Los demás dominios (`gateway`, `clinical-operations`, `revenue-cycle`, `compliance`) siguen como placeholders.

> English version: [README.md](./README.md).
