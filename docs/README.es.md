# Carpeta `docs`

Esta carpeta contiene la **documentación transversal** del monorepo: guías de arquitectura, decisiones técnicas, convenciones, procesos, y cualquier material compartido entre aplicaciones, pipelines, agentes y workflows.

- **Propósito principal**: tener un punto único para la documentación “global” del proyecto (no específica de una sola app/agente).
- **Recomendación**: organiza la documentación por temas (arquitectura, despliegue, datos, seguridad, observabilidad, etc.) y mantén enlaces desde los READMEs de cada componente hacia estas guías.


docs/
├── README.md
├── README.es.md
│
├── audit/                      ← auditorías técnicas (serialización API + rendimiento frontend)
│   ├── serialization-audit.md
│   ├── AUDIT.md
│   ├── REPORT.md
│   ├── before/
│   ├── after/
│   └── final/
│
├── architecture/
│   ├── ARCHITECTURE_PROPOSAL.md
│   └── ARCHITECTURE_PROPOSAL.es.md
│
├── data-contract/              ← análisis CSV de incidencias (hito previo)
│   ├── CONTEXT-HealthCore.md
│   ├── CONTEXT-HealthCore.es.md
│   ├── functional-design-analyze.md
│   └── functional-design-analyze.es.md
│
├── supplier-directory/         ← directorio de proveedores
│   ├── CONTEXT-HealthCore.md
│   └── CONTEXT-HealthCore.es.md
│
├── incident-manager/           ← gestor de incidencias (CONTEXT + ver scripts/seed_incidents.py, packages/shared)
│   ├── CONTEXT-HealthCore.md
│   └── CONTEXT-HealthCore.es.md
│
├── telemetry/                  ← plan de telemetría (solo diseño; aún sin captura)
│   ├── CONTEXT-healthcore.md
│   ├── CONTEXT-healthcore.es.md
│   ├── telemetry-plan.md
│   ├── telemetry-plan.es.md
│   └── event-schemas.json
├── audit/                      ← auditoría de rendimiento (Lighthouse) + informe de caching
│   ├── AUDIT.md
│   ├── REPORT.md
│   ├── CACHING_REPORT.md
│   ├── before/ | after/ | final/
│   └── README.md
│
├── api/                  (futuro)
│
├── decisions/            (futuro)
│
├── diagrams/             (futuro)
│
└── sprint-notes/         (futuro)