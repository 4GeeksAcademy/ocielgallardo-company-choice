# HealthCore Telemetry Plan

**Company:** HealthCore  
**Milestone:** Telemetry Plan (design only — no capture code)  
**Source of truth:** [CONTEXT-healthcore.md](./CONTEXT-healthcore.md)  
**Schema catalog:** [event-schemas.json](./event-schemas.json)  
**Spanish twin:** [telemetry-plan.es.md](./telemetry-plan.es.md)

---

## 1. Purpose and scope

Operations and management raised an RFI: can the running inventory system (and the rest of the HealthCore apps that staff or processes touch) produce actionable business information? This document answers that RFI with a design catalogue: what to capture, why, and how each event should travel (batch vs stream), before any instrumentation is written.

**Gold rule:** if the sentence cannot be completed, the event does not exist —

> We capture `[event_type]` because we need to know `[hypothesis]`, which lets us take `[concrete decision]`.

**In scope**

- Mandatory inventory metrics from CONTEXT (P0 floor).
- Extended catalogue across backoffice, public website, jobs, and platform health (P1/P2 ceiling).
- Event envelope, JSON Schema contracts, priority, and pipeline mode.

**Out of scope (this milestone)**

- Capture/instrumentation code in FastAPI or Next.js.
- Storage pipeline, dashboards, or seed generation for CONTEXT §5.
- Inventing PHI or patient-linked fields.

---

## 2. Regulatory rules (HIPAA / UK GDPR)

Events describe **supplies, stock, operators, and process outcomes** — never patients.

| Allowed | Forbidden (even as test data) |
| --- | --- |
| `clinic_id`, `country` (`US`/`UK`), `department` / service type | Patient name, MRN, diagnosis |
| Staff `userId` (TinyDB id / UUID string) | Patient identifiers of any kind |
| Product SKU, category, quantity, vendor name | Intake free-text reasons from the public form |
| Incident id, category, origin, status codes | Narrative fields that may embed PHI |

`department` means the **clinical service area where a supply was consumed** (e.g. `general_consultation`, `chronic_care`), not the staff member’s HR org unit.

Website and talent telemetry may use codes (`clinic_id`, `country`, stage enums). They must not put names, emails, or clinical free text into `properties`.

---

## 3. Entity and code mapping

Plan names follow CONTEXT exactly. Runtime code uses HealthCore inventory names.

| Plan (CONTEXT) | Runtime today | Primary emit points |
| --- | --- | --- |
| `Product` | `MedicalSupply` (`medical_supplies`) | `POST /inventory/products`, list/get products |
| `InboundOrder` | `SupplyDelivery` | `POST /inventory/orders/inbound` |
| `OutboundOrder` | `SupplyConsumption` | `POST /inventory/orders/outbound` |
| `clinic` | `clinic_id` (1–12, not a FK) | Order payloads |
| `department` | **Not yet on** `SupplyConsumption` | Required on outbound events when instrumented |
| Stock | Computed: deliveries − consumptions | Never a writable column |

### `product_category` mapping (event vocabulary → code)

Telemetry enums: `medication` | `ppe` | `consumable` | `equipment`.

| Code `MedicalSupply.category` | Event `product_category` |
| --- | --- |
| `ppe` | `ppe` |
| `medications` | `medication` |
| `consumables` | `consumable` |
| `wound_care` | `consumable` |
| `diagnostics` | `consumable` |
| *(no equipment seed yet)* | `equipment` when introduced |

Do not invent a third vocabulary in the plan. Instrumenters translate at emit time.

---

## 4. Event envelope

Every event uses this envelope. Payload-specific fields live under `properties`.

| Field | Type | Purpose |
| --- | --- | --- |
| `eventId` | string (UUID) | Idempotency and deduplication |
| `timestamp` | string (ISO 8601 UTC) | Ordering and time windows |
| `sessionId` | string \| null | Tie UI session to API calls |
| `userId` | string | Staff actor, or `system` / `job:*` for automated processes |
| `event_type` | string | Taxonomy `entity_action` |
| `schemaVersion` | string (semver) | Evolve payloads without breaking consumers |
| `requestId` | string \| null | Correlate frontend → FastAPI → logs |
| `properties` | object | Event-specific payload |

**Minimum inventory `properties`** (CONTEXT): `clinic_id`, `country`, `product_id`, `product_category`, `quantity`, and `department` only when applicable.

Full contracts: [event-schemas.json](./event-schemas.json).

---

## 5. Batch vs stream

| Mode | Business need | Typical use |
| --- | --- | --- |
| **Stream** | Know within seconds | Stock alerts, security/control rejections, auth anomalies, 5xx |
| **Batch** | Periodic aggregates suffice | Purchasing totals, consumption rates, expiry scans, daily login counts |

Rule of thumb: if Marcus or Claire would page someone at 14:00, use stream; if Dr. Okonkwo needs a Monday morning chart, use batch (optionally rolled up from stream).

---

## 6. P0 — Mandatory metrics (CONTEXT floor)

These five must be instrumented end-to-end by the end of the telemetry project series. They are designed for later aggregation by clinic and country.

### 6.1 `inbound_order_created`

| | |
| --- | --- |
| **Fires when** | A clinic registers receipt of supplies from a vendor |
| **Gold rule** | We capture `inbound_order_created` because we need to know how much and what supply is purchased by clinic and vendor, which lets us consolidate purchasing and negotiate better vendor terms |
| **Emit** | After successful `POST /inventory/orders/inbound` (`create_delivery`) |
| **Mode** | Batch |
| **Extra properties** | `vendor_name`, `sku`, `unit`, `order_id` |

### 6.2 `outbound_order_created`

| | |
| --- | --- |
| **Fires when** | A clinic registers consumption of a supply in a department’s care activity |
| **Gold rule** | We capture `outbound_order_created` because we need to know which supplies are consumed most and at what rate by clinic and department, which lets us adjust automatic replenishment of critical supplies per clinic |
| **Emit** | After successful `POST /inventory/orders/outbound` (`create_consumption`) |
| **Mode** | Batch |
| **Extra properties** | `department` (required), `consumption_type` (`clinical_use` \| `expiry_waste`), `sku`, `order_id` |

Answers: “How many outbound orders per day?”

### 6.3 `stock_threshold_triggered`

| | |
| --- | --- |
| **Fires when** | Stock of a supply at a clinic falls below the configured minimum |
| **Gold rule** | We capture `stock_threshold_triggered` because we need to know how often a clinic runs short of a critical supply, which lets us prioritise urgent restocking and escalate to Marcus (Clinical Operations) |
| **Emit** | After outbound (and optionally after inbound recalculation) when `current_stock < min_stock`; optional daily reconciliation job |
| **Mode** | Stream |
| **Extra properties** | `current_stock`, `min_stock_threshold`, `threshold_band` (`low` \| `critical`) |

UI today uses bands critical &lt; 5 and low &lt; 15 (`uis/backoffice/types/inventory.ts`). Target state: configurable `min_stock` per product/clinic.

### 6.4 `direct_stock_edit_rejected`

| | |
| --- | --- |
| **Fires when** | A user attempts to modify stock directly (outside an order) and the system rejects it |
| **Gold rule** | We capture `direct_stock_edit_rejected` because we need to know if staff attempt to bypass supply traceability controls, which lets us reinforce training or permissions at the clinic where this happens most |
| **Emit** | Explicit reject paths: `PUT`/`PATCH` on product stock, forbidden `current_stock` in create/update body, middleware on non-order inventory mutations → 403/405 + event |
| **Mode** | Stream |
| **Extra properties** | `attempted_path`, `http_status`, `rejection_reason` (`direct_stock_mutation_forbidden`); `department` N/A |

**Not this event:** outbound `400 Insufficient stock` (that is `outbound_order_rejected` in P1).

### 6.5 `supply_expiry_flagged`

| | |
| --- | --- |
| **Fires when** | A supply batch approaches expiry (e.g. within 30 days) |
| **Gold rule** | We capture `supply_expiry_flagged` because we need to know which supplies are about to expire before they become waste or a compliance risk, which lets us prioritise use or controlled disposal of that batch |
| **Emit** | Scheduled job (daily) reading `Product.expiry_date` |
| **Mode** | Batch |
| **Extra properties** | `expiry_date`, `days_to_expiry`, `batch_id` (when lot tracking exists); `department` N/A; `quantity` = remaining stock for that product/clinic |

CONTEXT requires expiry on the `Product` model for consistent cross-clinic computation.

---

## 7. Instrumentation gaps (target state)

Documented so implementers know what the runtime still lacks. This plan describes the target; it does not change code.

| Gap | Impact | Target |
| --- | --- | --- |
| No `expiry_date` on `MedicalSupply` | `supply_expiry_flagged` not computable | Add `expiry_date` on `Product` |
| No `min_stock` in API | Thresholds are UI magic numbers | Persist min stock per product/clinic |
| No `department` on `SupplyConsumption` | Outbound CONTEXT properties incomplete | Require `department` on outbound create |
| No stock write endpoint | Rejections are silent (405 / ignored extras) | Explicit reject + emit `direct_stock_edit_rejected` |
| Clinic master data | Aggregation by region incomplete | TODO: formal clinic registry (id → country, state/region) |

---

## 8. Application surface map

Any human or process touch is a data opportunity. Inventory is the floor; the rest prevents a “minimum-only” plan.

| Zone | Surfaces | Actor |
| --- | --- | --- |
| A Inventory | Products list, inbound/outbound forms, order history | Staff |
| B Auth & account | Login, register, logout, forgot/reset/change password, profile | Staff |
| C Incidents | List/filter, create, status patch, summary, CSV analyze/export | Staff |
| D Suppliers | Create, list/filter, rate, status, delete | Staff |
| E People & Talent | `/applications`, `/candidates/[id]` | Staff (workforce PII, not PHI) |
| F Placeholders | Patients, Appointments, Billing, Claims, Reports | Staff (page views only until built) |
| G Website | Home, `/application` intake (demo submit) | Public |
| H Jobs / internal | Inventory/supplier/incident seeds, Resend email, future expiry scan | `system` / `job:*` |
| I Platform | HTTP 4xx/5xx, validation handler, latency | Platform |

---

## 9. Extended catalogue (P1 / P2)

Each row satisfies the gold rule. Identifiers match [event-schemas.json](./event-schemas.json).

### 9.1 Inventory extras (P1)

| `event_type` | Hypothesis → decision | Mode | Emit |
| --- | --- | --- | --- |
| `product_created` | Know catalogue growth and category mix → plan stock coverage | Batch | `POST /inventory/products` 201 |
| `outbound_order_rejected` | Know validation/stock failures by product → fix UX and training | Batch | Outbound 400 (e.g. insufficient stock) |
| `inbound_order_rejected` | Know bad inbound payloads → fix forms / vendor data quality | Batch | Inbound 400/422 |
| `inventory_form_started` | Know which inventory flows are opened → prioritise UX | Batch | Inbound/outbound form mount |
| `inventory_form_abandoned` | Know mid-flow drop-off → simplify forms | Batch | Form started, no submit within session window |

### 9.2 Auth (P1 — tech lead questions)

| `event_type` | Hypothesis → decision | Mode | Emit |
| --- | --- | --- | --- |
| `login_succeeded` | Know successful access volume → capacity and shift planning | Batch | `POST /auth/login` 200 |
| `login_failed` | Know failed attempts per day → detect brute force / bad UX | Stream | `POST /auth/login` 401 |
| `logout_completed` | Know session endings → session hygiene metrics | Batch | Client clear session |
| `user_registered` | Know staffing of backoffice accounts → access governance | Batch | `POST /users` 201 |
| `password_reset_requested` | Know reset demand (no email enumeration in props) → support load | Batch | `POST /auth/forgot-password` |
| `password_reset_completed` | Know completion rate of resets → fix token/email friction | Batch | `POST /auth/reset-password` 200 |
| `password_reset_failed` | Know invalid/expired tokens → tune TTL and messaging | Stream | Reset 400 |
| `password_changed` | Know authenticated password changes → security audit trail | Batch | `POST /auth/change-password` 200 |
| `session_unauthorized` | Know expired/missing tokens hitting APIs → session UX | Stream | 401 on protected routes |

Auth `properties`: never store password or reset token. Prefer opaque `userId` or hashed email identifier.

### 9.3 UX navigation (P1)

| `event_type` | Hypothesis → decision | Mode | Emit |
| --- | --- | --- | --- |
| `page_viewed` | Know which sections operators visit most (including placeholders) → roadmap priority | Batch | Route change in backoffice/website |
| `form_abandoned` | Know flows abandoned mid-way → reduce friction | Batch | Form start without submit |

`page_viewed.properties`: `path`, `app` (`backoffice` \| `website`), optional `referrer_path`. No PHI.

### 9.4 Incidents (P1)

| `event_type` | Hypothesis → decision | Mode | Emit |
| --- | --- | --- | --- |
| `incident_created` | Know incident volume by origin/branch/category → ops staffing | Batch | `POST /api/incidents` 201 |
| `incident_validation_failed` | Know which fields fail most → improve form validation UX | Batch | Create 400 field errors |
| `incident_status_changed` | Know lifecycle throughput → SLA and bottlenecks | Batch | `PATCH .../status` 200 |
| `incident_status_rejected` | Know illegal transitions → training / UI guards | Batch | Illegal transition 400 |
| `incident_csv_analyzed` | Know analysis usage → invest in CSV tooling | Batch | `POST /api/incidents/analyze` 200 |
| `incident_csv_rejected` | Know malformed uploads → improve templates/docs | Batch | Analyze 400 |
| `incident_results_exported` | Know export demand → retention of results.csv | Batch | `GET .../results/export` 200 |
| `incident_summary_viewed` | Know dashboard usage → keep summary useful | Batch | Summary page / `GET .../summary` |

Properties: ids, status, category, origin, branch codes — not free-text that may contain PHI.

### 9.5 Suppliers (P1)

| `event_type` | Hypothesis → decision | Mode | Emit |
| --- | --- | --- | --- |
| `supplier_created` | Know directory growth → procurement coverage | Batch | `POST /suppliers` 201 |
| `supplier_rate_updated` | Know rate changes → cost negotiations with inbound data | Batch | `PATCH .../rate` |
| `supplier_status_changed` | Know activations/suspensions → vendor risk | Batch | `PATCH .../status` |
| `supplier_deleted` | Know removals → audit directory hygiene | Batch | `DELETE /suppliers/{id}` |

Joins conceptually with `inbound_order_created.vendor_name` for consolidation decisions.

### 9.6 People & Talent (P2)

| `event_type` | Hypothesis → decision | Mode | Emit |
| --- | --- | --- | --- |
| `talent_list_filtered` | Know recruiter filter patterns → hiring UX | Batch | Applications filters applied |
| `talent_record_created` | Know pipeline intake volume → Diane’s time-to-hire KPIs | Batch | Create application record |
| `talent_candidate_viewed` | Know which candidates get attention → pipeline bottlenecks | Batch | Open `/candidates/[id]` |

Workforce PII: use record ids and stage/status enums only — no CV text or national IDs in events.

### 9.7 Website public (P2)

| `event_type` | Hypothesis → decision | Mode | Emit |
| --- | --- | --- | --- |
| `website_page_viewed` | Know public traffic to home vs intake → patient access investment | Batch | Website route view |
| `intake_form_started` | Know how many start intake → conversion funnel | Batch | Form focus/mount |
| `intake_form_submitted` | Know demo/real submit volume by country/clinic code → access demand | Batch | Submit success (codes only) |
| `intake_form_validation_failed` | Know which fields block submit → form UX | Batch | Client validation fail |

**Forbidden in properties:** `fullName`, `email`, `phone`, `reason`, or any patient narrative.

### 9.8 Platform / jobs (P1–P2)

| `event_type` | Hypothesis → decision | Mode | Emit |
| --- | --- | --- | --- |
| `http_request_failed` | Know 4xx/5xx rates by route → fix reliability before clinics call | Stream (5xx) / Batch (4xx aggregates) | Global exception / response middleware |
| `api_unhandled_error` | Know unexpected 500s → page on-call | Stream | Unhandled exception handler |
| `email_send_failed` | Know Resend failures without leaking addresses → fix email path | Stream | Password-reset email send failure |
| `job_run_completed` | Know seed/expiry job health → ops confidence | Batch | End of job (`job_name`, `status`, `duration_ms`) |

---

## 10. Priority and pipeline sketch

| Priority | Events | Pipeline |
| --- | --- | --- |
| **P0** | Five CONTEXT mandatory types | Stream: `stock_threshold_triggered`, `direct_stock_edit_rejected`. Batch: inbound/outbound created, `supply_expiry_flagged` |
| **P1** | Auth, UX page/form, inventory extras, incidents, suppliers, platform errors | Stream for security/5xx; batch for aggregates |
| **P2** | Talent, website intake funnel | Batch |

```text
[Backoffice | Website | Jobs]
          │
          ▼
   Event envelope (+ schemaVersion)
          │
     ┌────┴────┐
     ▼         ▼
  Stream     Batch
  (alerts,   (hourly/daily
   security)  rollups → dashboards)
```

**Correlation:** generate `requestId` on the client (or gateway), pass as header (e.g. `X-Request-Id`), echo in API logs and telemetry so one user action links UI → FastAPI → event.

**schemaVersion policy:** start at `1.0.0`. Additive optional fields → minor bump. Breaking rename/remove → major bump; keep dual-read window.

---

## 11. Open TODOs

- TODO: Confirm formal clinic master list (12 clinics → `clinic_id`, country, state/region) for executive aggregation.
- TODO: Confirm expiry-scan schedule (default assumption: daily 06:00 UTC, window window 30 days).
- TODO: Confirm whether `equipment` category appears in seed before capture milestone.
- TODO: CONTEXT §5 seed volumes are for a later capture/storage milestone — not generated in this design pass.

---

## 12. Delivery notes

- Documentation-only change; no automated tests executed.
- Mandatory `event_type` names and inventory property floors match [CONTEXT-healthcore.md](./CONTEXT-healthcore.md).
- Spanish plan uses the same identifiers: [telemetry-plan.es.md](./telemetry-plan.es.md).
