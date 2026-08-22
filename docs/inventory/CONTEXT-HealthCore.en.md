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
