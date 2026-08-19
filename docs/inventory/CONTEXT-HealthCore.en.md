Skip to content
4GeeksAcademy
ai-engineering-syllabus
Repository navigation
Code
Issues
32
 (32)
Pull requests
Actions
Projects
Security and quality
Insights
Files
Go to file
t
T
.cursor
assets
content
contexts
00-general-contexts
01-web-fundamentals
02-coding-fundamentals
03-frontend-development
05-backend-development
CONTEXT-brasaland.en.md
CONTEXT-brasaland.es.md
CONTEXT-healthcore.en.md
CONTEXT-healthcore.es.md
CONTEXT-nexova.en.md
CONTEXT-nexova.es.md
CONTEXT-trackflow.en.md
CONTEXT-trackflow.es.md
06-telemetry-data-pipelines
07-trainning-rag
08-agent-engineering
09-agentic-workflows
10-realtime
audit-log
centralized-incident-manager
cybersecurity-analysis
federated-authentication
incidents-file-analysis
openclaw-onboarding-agent
roles-permissions
sales-forecasting
supplier-directory
README.es.md
README.md
lessons
projects
docs
marketing
.gitignore
README.md
package.json
pnpm-lock.yaml
You’re making changes in a project you don’t have write access to. Submitting a change will write it to a new branch in your fork GallaGit/ai-engineering-syllabus, so you can send a pull request.
ai-engineering-syllabus/content/contexts/05-backend-development
/
CONTEXT-healthcore.en.md
in
main

Edit

Preview
Indent mode

Spaces
Indent size

4
Line wrap mode

Soft wrap
Editing CONTEXT-healthcore.en.md file contents


1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
# CONTEXT — Milestone 5: Backend Inventory Management

## Company: HealthCore

**Path:** `05-backend-inventory-orm/CONTEXT-healthcore.md`

---

## Your Company

**HealthCore** is an outpatient healthcare services company operating 12 clinics across the USA (Texas, Florida, Georgia) and the UK (London, Manchester). Each clinic consumes medical supplies daily — syringes, PPE, wound care materials, rapid diagnostic tests, and medications — and receives restocking shipments from certified healthcare vendors.

Tracking what supplies are available at each clinic is both an operational necessity and a compliance requirement. Running out of PPE mid-shift or using expired supplies creates clinical risk. Until now, each location has managed stock in a local spreadsheet with no central visibility.

**James Osei (CTO)** has prioritised this as part of the HealthCore Digital platform build.

> **From James (CTO) — Jira ticket HCR-0188:**
> "We need a medical supply inventory API as the foundation for the clinical operations dashboard. Supply entries are deliveries from vendors. Supply exits are clinical consumptions logged by clinic staff. Stock is always the net of entries minus exits — direct modification is not allowed. All routes under `/inventory`. User UUIDs come from TinyDB. Claire has confirmed: supply inventory data is operational, not PHI — no HIPAA barriers on this API, but access must be authenticated."

---

## Entity Names and Field Specification

Use these names exactly in your models, schemas, and API responses.

### `MedicalSupply` (maps to README's `Product`)

| Field           | Type       | Notes                                                                                            |
| --------------- | ---------- | ------------------------------------------------------------------------------------------------ |
| `id`            | `int` (PK) | Auto-increment                                                                                   |
| `name`          | `str`      | e.g., `"Nitrile gloves (box of 100)"`, `"Rapid strep test kit"`                                  |
| `sku`           | `str`      | Internal catalogue code, e.g., `"HCR-PPE-001"`, `"HCR-DIAG-003"`                                 |
| `category`      | `str`      | `"ppe"`, `"wound_care"`, `"diagnostics"`, `"medications"`, `"consumables"`                       |
| `unit`          | `str`      | `"box"`, `"unit"`, `"pack"`, `"vial"`                                                            |
| `country`       | `str`      | `"US"` or `"UK"` — regulatory jurisdiction                                                       |
| `current_stock` | `int`      | **Computed field — not stored.** Derived from supply movements. Include in response schema only. |

### `SupplyDelivery` (maps to README's `InboundOrder`)

A vendor shipment received at a HealthCore clinic.

| Field         | Type                       | Notes                                                                     |
| ------------- | -------------------------- | ------------------------------------------------------------------------- |
| `id`          | `int` (PK)                 | Auto-increment                                                            |
| `supply_id`   | `int` (FK → MedicalSupply) |                                                                           |
| `quantity`    | `int`                      | Units received                                                            |
| `vendor_name` | `str`                      | e.g., `"MedLine Industries"`, `"Cardinal Health UK"`                      |
| `clinic_id`   | `int`                      | Receiving clinic (1–12). Not a FK — clinic data is managed separately.    |
Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the next interactive element on the page.
Sin archivos seleccionados
Attach files by dragging & dropping, selecting or pasting them.
