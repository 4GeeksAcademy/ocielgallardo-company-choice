# Carpeta `docs`

Esta carpeta contiene la **documentación transversal** del monorepo: guías de arquitectura, decisiones técnicas, convenciones, procesos, y cualquier material compartido entre aplicaciones, pipelines, agentes y workflows.

- **Propósito principal**: tener un punto único para la documentación “global” del proyecto (no específica de una sola app/agente).
- **Recomendación**: organiza la documentación por temas (arquitectura, despliegue, datos, seguridad, observabilidad, etc.) y mantén enlaces desde los READMEs de cada componente hacia estas guías.


docs/
├── README.md
├── README.es.md
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
├── api/                  (futuro)
│
├── decisions/            (futuro)
│
├── diagrams/             (futuro)
│
└── sprint-notes/         (futuro)