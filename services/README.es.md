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

- `incidents_analysis/` — análisis CSV de incidentes de pacientes HealthCore (`models`, `csv_reader`, `validator`, `analyzer`, `exporter`). Lo consumen `scripts/analyze.py` y la capa de dominio de la API.
- `app/` — aplicación FastAPI (`services/app/main.py`) en capas:
  - `core/` — TinyDB (`database.py`), seed de proveedores (`seed.py`), helpers JWT/password (`security.py`), `deps.py` (`get_current_user`)
  - `models/` — modelos Pydantic (`supplier`, `user`, `profile`)
  - `domain/` — orquestación de negocio (`supplier_service`, `incident_service`, `user_service`, `profile_service`)
  - `routers/` — solo HTTP:
    - `incidents.py` → `POST /api/incidents/analyze`, `GET /api/incidents/results/export`
    - `suppliers.py` → CRUD + filtros + rate/status del directorio de proveedores (**requiere Bearer**)
    - `users.py` → CRUD de credenciales (`POST` público; `GET/PUT/DELETE` requieren Bearer; PUT/DELETE dueño o admin)
    - `auth.py` → `POST /auth/login`, `GET /auth/me` (JWT)
    - `profiles.py` → `GET/PUT /profiles/me` (JWT)

Notas de auth (AUTH-01, rama `feature/auth`):

- Contraseñas con `passlib` + `bcrypt` (fijar `bcrypt==4.0.1` por compatibilidad con passlib).
- JWT con `python-jose`; `SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES` en el `.env` de la raíz (ver `.env.example`).
- User y Profile solo en TinyDB (no tablas de usuario en PostgreSQL/Supabase).
- Todas las rutas `/suppliers` y las de `/users` no públicas requieren `Authorization: Bearer <token>` (401 sin él).

Desde la raíz del repo:

```bash
uv run python -m uvicorn services.app.main:app --reload
uv run python -m services.app.core.seed
```

### Rutas de datos en runtime usadas por `services/app`

- `data/process/results.csv` — último resumen de incidentes exportado.
- `data/process/suppliers/suppliers.json` — archivo TinyDB del directorio de proveedores.
- `data/process/auth/auth.json` — TinyDB de users y profiles (en `.gitignore`).

## Estado

La lógica de análisis de incidentes vive en `incidents_analysis/` y se reutiliza vía `app/domain/incident_service`. AUTH-01 aplica JWT a users (salvo registro) y a todas las rutas de suppliers; incidents siguen públicas por ahora. Los demás dominios (`gateway`, `clinical-operations`, `revenue-cycle`, `compliance`) siguen como placeholders.

> English version: [README.md](./README.md).
