# Performance audit — HealthCore

Evidencia y documentación del hito **Auditoría de Rendimiento Frontend** (4Geeks Academy).

| Documento | Contenido |
|-----------|-----------|
| [`AUDIT.md`](./AUDIT.md) | Causa raíz (P1–P7), tablas KPI, checklist |
| [`REPORT.md`](./REPORT.md) | Informe en español, deltas, notas PR |

## Evidencia Lighthouse

| Carpeta | Cuándo | Entorno |
|---------|--------|---------|
| [`before/`](./before/) | Baseline 2026-08-25 | `next dev` |
| [`after/`](./after/) | 2026-08-28, pre-P7 lazy | Docker prod |
| [`final/`](./final/) | 2026-08-28, post-P7 | Docker prod |

Extraer métricas: `node scripts/extract-lighthouse-kpis.mjs audit/<pass>/*.html --markdown`
