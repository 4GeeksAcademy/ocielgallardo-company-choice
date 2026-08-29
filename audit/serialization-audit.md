# Serialization Audit — HealthCore API

Location: `audit/serialization-audit.md`  
Branch: `feature/serialization-audit`  
Scope: `services/app` FastAPI surface. Consumer: `uis/backoffice` only.  
Phase 1 status: **closed** (every endpoint classified below).

## Classification (required)

Every endpoint must have exactly one of:

| Status | Meaning |
|--------|---------|
| **1. Ya serializado** | Explicit Pydantic `response_model` (or intentional non-JSON contract such as CSV `FileResponse`). Output fields are intentional; no raw ORM/TinyDB dump; no secrets. |
| **2. Parcialmente serializado** | Has a `response_model`, but the contract is imperfect: e.g. response schema inherits from a write/create model, or projection is not separated from persistence concerns. |
| **3. Sin serializar** | JSON handler returns a bare `dict` / ORM / domain object with **no** `response_model`. Contract undefined. |

---

## Master checklist (Phase 1 close)

| # | Method | Path | Response schema | Classification | Notes |
|---|--------|------|-----------------|----------------|-------|
| 1 | POST | `/auth/login` | `TokenResponse` | **1. Ya serializado** | Token only; no user/hash/email. |
| 2 | GET | `/auth/me` | `AuthMeResponse` | **1. Ya serializado** | `email`, `role`, `profile`. No credentials. |
| 3 | POST | `/auth/forgot-password` | `MessageResponse` | **1. Ya serializado** | `{message}` only; no email echo. |
| 4 | POST | `/auth/reset-password` | `MessageResponse` | **1. Ya serializado** | `{message}` only. |
| 5 | POST | `/auth/change-password` | `MessageResponse` | **1. Ya serializado** | `{message}` only. |
| 6 | POST | `/users` | `UserPublic` | **1. Ya serializado** | Public projection; `role` not accepted on create. |
| 7 | GET | `/users` | `list[UserPublic]` | **1. Ya serializado** | Lean public fields. |
| 8 | GET | `/users/{user_id}` | `UserPublic` | **1. Ya serializado** | |
| 9 | PUT | `/users/{user_id}` | `UserPublic` | **1. Ya serializado** | Password write-only. |
| 10 | DELETE | `/users/{user_id}` | `DetailResponse` | **1. Ya serializado** | `{detail}`. |
| 11 | GET | `/profiles/me` | `ProfilePublic` | **1. Ya serializado** | |
| 12 | PUT | `/profiles/me` | `ProfilePublic` | **1. Ya serializado** | Write limited to name/phone/address. |
| 13 | POST | `/suppliers` | `Supplier` | **2. Parcialmente serializado** | Has schema, but `Supplier` extends `SupplierCreate` (write validators tied to read). |
| 14 | GET | `/suppliers` | `list[Supplier]` | **2. Parcialmente serializado** | Same shared model; fields OK for UI, inheritance debt remains. |
| 15 | GET | `/suppliers/{id}` | `Supplier` | **2. Parcialmente serializado** | Same as above. |
| 16 | PATCH | `/suppliers/{id}/rate` | `Supplier` | **2. Parcialmente serializado** | Same as above. |
| 17 | PATCH | `/suppliers/{id}/status` | `Supplier` | **2. Parcialmente serializado** | Same as above. |
| 18 | DELETE | `/suppliers/{id}` | `DetailResponse` | **1. Ya serializado** | `{detail}`. |
| 19 | POST | `/api/incidents/analyze` | `IncidentAnalysisSummary` | **1. Ya serializado** | Aggregates only; no `patient_id` (PHI). |
| 20 | GET | `/api/incidents/results/export` | `FileResponse` (CSV) | **1. Ya serializado** | Non-JSON file download; not an ORM dump. |
| 21 | GET | `/api/incidents/summary` | `IncidentSummary` | **1. Ya serializado** | |
| 22 | POST | `/api/incidents` | `Incident` | **1. Ya serializado** | Full detail projection. |
| 23 | GET | `/api/incidents` | `list[IncidentListItem]` | **1. Ya serializado** | List projection without timestamps. |
| 24 | GET | `/api/incidents/{id}` | `Incident` | **1. Ya serializado** | Detail includes timestamps. |
| 25 | PATCH | `/api/incidents/{id}/status` | `Incident` | **1. Ya serializado** | |
| 26 | GET | `/inventory/products` | `list[MedicalSupplyResponse]` | **1. Ya serializado** | ORM separated from response; no nested relations. |
| 27 | POST | `/inventory/products` | `MedicalSupplyResponse` | **1. Ya serializado** | |
| 28 | GET | `/inventory/products/{id}` | `MedicalSupplyResponse` | **1. Ya serializado** | |
| 29 | POST | `/inventory/orders/inbound` | `SupplyDeliveryResponse` | **1. Ya serializado** | |
| 30 | POST | `/inventory/orders/outbound` | `SupplyConsumptionResponse` | **1. Ya serializado** | |
| 31 | GET | `/inventory/orders` | `list[InventoryOrderListItem]` | **1. Ya serializado** | Lean history columns only. |

### Phase 1 totals (current code)

| Classification | Count |
|----------------|-------|
| **1. Ya serializado** | 26 |
| **2. Parcialmente serializado** | 5 (all supplier JSON CRUD/list/detail/rate/status) |
| **3. Sin serializar** | **0** |

Phase 1 gate: every endpoint has a classification → **pass**.  
Minimum milestone gate (no JSON endpoint without `response_model`) → **pass** (`Sin serializar = 0`).

---

## Target payloads (endpoints that needed work)

### Auth

- `GET /auth/me` → `email`, `role`, `profile: ProfilePublic | null` (never `hashed_password`).
- Password flows → `{ "message": "ok" }` only.

### Deletes

- `DELETE /users/{id}`, `DELETE /suppliers/{id}` → `{ "detail": "…" }` via `DetailResponse`.

### Incidents

- `POST /analyze` → aggregate summary only (PHI-safe).
- `GET /api/incidents` → `IncidentListItem` without `created_at` / `updated_at`.

### Inventory

- `GET /inventory/orders` → `order_type`, `id`, `supply_name`, `quantity`, `created_at`, `user_uuid`.

### Remaining partial (optional follow-up)

- TODO: Split `SupplierResponse` from `SupplierCreate` so suppliers move from **2** → **1**.
- TODO: Optionally unify delete bodies on `MessageResponse.message`.

---

## Verification evidence

OpenAPI (`app.openapi()`) lists an explicit JSON schema component for every JSON route above.  
`GET /api/incidents/results/export` is CSV `FileResponse` (no JSON body schema by design).
