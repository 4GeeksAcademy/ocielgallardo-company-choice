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

## Estado

No hay APIs implementadas todavía. Esta carpeta solo prepara la arquitectura.
