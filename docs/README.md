# `docs` folder

This folder holds **cross-cutting documentation** for the monorepo: architecture guides, technical decisions, conventions, processes, and any material shared across applications, pipelines, agents, and workflows.

- **Main purpose**: provide a single place for “global” project documentation (not tied to one app or agent only).
- **Recommendation**: organize docs by topic (architecture, deployment, data, security, observability, etc.) and keep links from each component’s README to these guides.

> _Spanish version: [README.es.md](./README.es.md)._

docs/
├── README.md
├── README.es.md
│
├── audit/                      ← technical audits (serialization API + frontend performance)
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
├── data-contract/              ← CSV incident analysis (prior milestone)
│   ├── CONTEXT-HealthCore.md
│   ├── CONTEXT-HealthCore.es.md
│   ├── functional-design-analyze.md
│   └── functional-design-analyze.es.md
│
├── supplier-directory/         ← supplier directory milestone
│   ├── CONTEXT-HealthCore.md
│   └── CONTEXT-HealthCore.es.md
│
├── incident-manager/           ← centralized incident manager (CONTEXT + see scripts/seed_incidents.py, packages/shared)
│   ├── CONTEXT-HealthCore.md
│   └── CONTEXT-HealthCore.es.md
│
├── telemetry/                  ← telemetry plan (design docs; no capture code yet)
│   ├── CONTEXT-healthcore.md
│   ├── CONTEXT-healthcore.es.md
│   ├── telemetry-plan.md
│   ├── telemetry-plan.es.md
│   └── event-schemas.json
├── audit/                      ← frontend performance audit (Lighthouse) + caching report
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
