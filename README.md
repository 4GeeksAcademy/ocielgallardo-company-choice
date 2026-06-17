# AI Engineering Company Project — Student Template

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

_Base template for transversal projects in the AI Engineering Career Program — 4Geeks Academy._

> _Instrucciones disponibles en español en [README.es.md](./README.es.md)._

---

## Purpose

This repository is the **starter template** for transversal projects. You will work on real company scenarios (Brasaland, TrackFlow, Nexova), building deliverables that map to course milestones (Web, Programming, Backend, Telemetry, RAG, Agents, Workflows, Real-time).

- Create a template from this repository.
- Replace the placeholder `CONTEXT.md` with your assigned company context.
- Use `skills/` and the directory-level `README.md` files as working guidance.

---

## Current implementation progress (HealthCore)

This repository is no longer only a skeleton. It now includes concrete deliverables for the HealthCore scenario, covering Milestone 1 (Web) and core parts of Milestone 2 (Programming).

### 1) Web deliverables completed

- Full responsive landing page in `index.html`.
- Semantic structure (`header`, `nav`, `main`, `section`, `article`, `footer`).
- SEO and social metadata (Open Graph, Twitter cards).
- Structured data (JSON-LD) for organization/business context.
- Responsive and accessible form page in `application.html`.
- Frontend validation logic in `validation.js`.

### 2) TypeScript domain model and utilities completed

Implemented under `src/`:

- `src/types/models.ts`
	- Strongly typed entities for HealthCore business domain (company, departments, patients, appointments, invoices, predictions, alerts, filters).

- `src/utils/collections.ts`
	- Filtering utilities:
		- `findOneById`
		- `filterByCategory`
		- `filterByStatus`
		- `filterByProbabilityRange`
		- `filterCritical`
	- Sorting utilities:
		- `sortByField` (ascending/descending)
		- `sortByMultipleFields` (multi-field sorting)

- `src/utils/search.ts`
	- Search utilities:
		- `linearSearch`
		- `linearSearchUnsorted`
		- `linearSearchByField`
		- `binarySearchByNumber`
		- `binarySearchByField`

- `src/utils/transformations.ts`
	- Reporting and aggregation utilities:
		- `calculateNoShowRate`
		- `calculateInvoiceRejectionRate`
		- `generateCriticalAlerts`
		- `groupAlertsByStatus`
		- `countByCategory`
		- `calculateTotal`
		- `calculateAverage`
		- `calculateMax`
		- `calculateMin`

- `src/utils/validations.ts`
	- Context-aware business validations aligned with HealthCore context (including 22% no-show and 14% invoice rejection baselines).
	- Pre-processing validation orchestrator:
		- `validateRecordBeforeProcessing(...)`

### 3) Type validation command available

The project includes a clear TypeScript validation command in `packages/shared/package.json`:

```bash
cd /workspaces/ocielgallardo-company-choice/packages/shared
npm run test:types:models
```

This runs strict type checking against:

- `src/types/models.ts`
- `src/types/models.type-test.ts`

### 4) Manual visual playground for utilities

A temporary testing playground is available to manually validate utility outputs:

- `test.html`
- `test-playground.js`
- `test-data.js`

Run locally with:

```bash
npx http-server . -p 3000 -a 0.0.0.0
```

Then open:

`http://localhost:3000/test.html`

---

## Current status of the template

The repository provides the original folder structure plus active project implementation for HealthCore.

- `CONTEXT.md` has been replaced with HealthCore context and is actively used to drive implementation.
- There is no root `AGENTS.md` yet.
- Shared package metadata exists in `packages/shared/package.json` (`@repo/shared-types`) with a working TypeScript type-test command.

---

## Repository structure

```text
ai-engineering-company-project-monorepo/
├── README.md
├── README.es.md
├── CONTEXT.md                # Placeholder to be replaced with assigned context
├── agents/                   # Agent patterns/templates and tools docs
├── data/                     # raw, process, pipelines, eval
├── docs/                     # Project and architecture documentation
├── infra/                    # Docker, Terraform, deployment configs
├── internal/                 # CLIs, packaged migration scripts, internal utilities
├── mcps/                     # Model Context Protocol (MCP) Servers
├── packages/
│   └── shared/               # Shared package (@repo/shared-types)
├── scripts/                  # Script conventions/documentation
├── services/                 # APIs and background workers
├── shared/                   # Shared assets/conventions at repo level
├── skills/                   # Reusable agent skills
├── uis/                      # User interfaces (React, Next.js, Streamlit, HTML)
└── workflows/                # Automation/orchestration documentation
```

---

## How to start

1. **Use this repository as a template** and create your own project repo.
2. **Clone** your repository (or open it in Codespaces).
3. **Replace** `CONTEXT.md` with the full context for your assigned company.
4. **Review** each top-level folder `README.md` to understand intended responsibilities (`uis/`, `services/`, `data/`, `skills/`, etc.).
5. **Start implementing** milestone deliverables in `uis/` and `services/`, reusing `packages/shared/` and `data/` as needed.

---

## Milestones (reference)

| Milestone | Focus        | Typical deliverables                        |
| --------- | ------------ | ------------------------------------------- |
| 0         | Prework      | Environment setup, first prompts            |
| 1         | Web          | Corporate website, forms, SEO               |
| 2         | Programming  | Business logic, scoring, calculations       |
| 3         | AI-driven UI | AI-generated interfaces                     |
| 4         | Next.js      | Portals, loyalty app, operations UI         |
| 5         | Backend      | Central API (locations, menus, sales, etc.) |
| 6         | Telemetry    | Data pipeline, dashboards                   |
| 7         | RAG & Memory | Semantic knowledge base, search             |
| 8         | Agents       | Support, onboarding, training agents        |
| 9         | Workflows    | n8n automations                             |
| 10        | Real-time    | Live dashboards, alerts, streaming          |

---

## Links

- [4Geeks Academy — AI Engineering](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [How to start a coding project](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contributors

This template was built as part of the 4Geeks Academy AI Engineering Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) and [@alezanchezr](https://x.com/alesanchezr) and many other contributors. Find out more about our [AI Engineering Course](https://4geeksacademy.com/en/career-programs/ai-engineering), and [other courses](https://4geeksacademy.com/en/program-comparison).

You can find other templates and resources like this at the [4Geeks Academy GitHub page](https://github.com/4geeksacademy).

_This template is maintained by 4Geeks Academy for the AI Engineering track. For exclusive use in the programme._
