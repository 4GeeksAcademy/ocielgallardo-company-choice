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
	- `core/` — TinyDB (`database.py`) y seed de proveedores (`seed.py`)
	- `models/` — modelos Pydantic de proveedores
	- `domain/` — orquestación de negocio (`supplier_service`, `incident_service`)
	- `routers/` — solo HTTP:
		- `incidents.py` → `POST /api/incidents/analyze`, `GET /api/incidents/results/export`
		- `suppliers.py` → CRUD + filtros + rate/status del directorio de proveedores

Desde la raíz del repo:

```bash
python -m uvicorn services.app.main:app --reload
python -m services.app.core.seed
```

### Rutas de datos en runtime usadas por `services/app`

- `data/process/results.csv` — último resumen de incidentes exportado.
- `data/process/suppliers/suppliers.json` — archivo TinyDB del directorio de proveedores.

## Estado

La lógica de análisis de incidentes vive en `incidents_analysis/` y se reutiliza vía `app/domain/incident_service`. Los demás dominios (`gateway`, `clinical-operations`, `revenue-cycle`, `compliance`) siguen como placeholders.

> English version: [README.md](./README.md).
