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

## Implementado (Python, reutilizable por CLI / futura API)

- `incidents_analysis/` — análisis CSV de incidentes de pacientes HealthCore (`models`, `csv_reader`, `validator`, `analyzer`, `exporter`). Lo consume `scripts/analyze.py`.

## Estado

La lógica CLI de análisis de incidentes vive en `incidents_analysis/`. Las APIs HTTP de otros dominios siguen siendo placeholders.
