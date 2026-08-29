# Serialization Audit — HealthCore API

Location: `docs/audit/serialization-audit.md`  
Branch: `feature/serialization-audit`  
Scope: `services/app` FastAPI surface. Consumer: `uis/backoffice` only.  
**Milestone status: complete**  
Phase 1 status: **closed**  
Phase 2 status: **closed**

## Classification (required)

Every endpoint must have exactly one of:

| Status | Meaning |
|--------|---------|
| **1. Ya serializado** | Explicit Pydantic `response_model` (or intentional non-JSON contract such as CSV `FileResponse`). Output fields are intentional; no raw ORM/TinyDB dump; no secrets. |
| **2. Parcialmente serializado** | Has a `response_model`, but the contract is imperfect: e.g. response schema inherits from a write/create model, or projection is not separated from persistence concerns. |
| **3. Sin serializar** | JSON handler returns a bare `dict` / ORM / domain object with **no** `response_model`. Contract undefined. |

---

## Master checklist

All **31** endpoints below are classified **1. Ya serializado**. None remain partial or unserialized.

| # | Method | Path | Response schema | Classification | Notes |
|---|--------|------|-----------------|----------------|-------|
| 1 | POST | `/auth/login` | `TokenResponse` | **1. Ya serializado** | Token only; no user/hash/email. |
| 2 | GET | `/auth/me` | `AuthMeResponse` | **1. Ya serializado** | `email`, `role`, `profile`. Caller email allowed for profile UI. |
| 3 | POST | `/auth/forgot-password` | `MessageResponse` | **1. Ya serializado** | `{message}` only; no email echo. |
| 4 | POST | `/auth/reset-password` | `MessageResponse` | **1. Ya serializado** | `{message}` only. |
| 5 | POST | `/auth/change-password` | `MessageResponse` | **1. Ya serializado** | `{message}` only. |
| 6 | POST | `/users` | `RegisterResponse` | **1. Ya serializado** | `id`, `is_active`, `role`, `created_at` — **no email**. Input: `UserCreate` (no `role`). |
| 7 | GET | `/users` | `list[UserPublic]` | **1. Ya serializado** | Lean public fields. |
| 8 | GET | `/users/{user_id}` | `UserPublic` | **1. Ya serializado** | |
| 9 | PUT | `/users/{user_id}` | `UserPublic` | **1. Ya serializado** | Input: `UserUpdate`; password write-only. |
| 10 | DELETE | `/users/{user_id}` | `DetailResponse` | **1. Ya serializado** | `{detail}`. |
| 11 | GET | `/profiles/me` | `ProfilePublic` | **1. Ya serializado** | |
| 12 | PUT | `/profiles/me` | `ProfilePublic` | **1. Ya serializado** | Input: `ProfileUpdate` (name/phone/address only). |
| 13 | POST | `/suppliers` | `SupplierResponse` | **1. Ya serializado** | Input: `SupplierCreate`; response does not inherit write validators. |
| 14 | GET | `/suppliers` | `list[SupplierResponse]` | **1. Ya serializado** | Full card fields (UI uses all). |
| 15 | GET | `/suppliers/{id}` | `SupplierResponse` | **1. Ya serializado** | |
| 16 | PATCH | `/suppliers/{id}/rate` | `SupplierResponse` | **1. Ya serializado** | Input: `SupplierRateUpdate`. |
| 17 | PATCH | `/suppliers/{id}/status` | `SupplierResponse` | **1. Ya serializado** | Input: `SupplierStatusUpdate`. |
| 18 | DELETE | `/suppliers/{id}` | `DetailResponse` | **1. Ya serializado** | `{detail}`. |
| 19 | POST | `/api/incidents/analyze` | `IncidentAnalysisSummary` | **1. Ya serializado** | Aggregates only; no `patient_id` (PHI). |
| 20 | GET | `/api/incidents/results/export` | `FileResponse` (CSV) | **1. Ya serializado** | Non-JSON file download; not an ORM dump. |
| 21 | GET | `/api/incidents/summary` | `IncidentSummary` | **1. Ya serializado** | |
| 22 | POST | `/api/incidents` | `Incident` | **1. Ya serializado** | Input: `IncidentCreate`. |
| 23 | GET | `/api/incidents` | `list[IncidentListItem]` | **1. Ya serializado** | List without timestamps. |
| 24 | GET | `/api/incidents/{id}` | `Incident` | **1. Ya serializado** | Detail includes timestamps. |
| 25 | PATCH | `/api/incidents/{id}/status` | `Incident` | **1. Ya serializado** | Input: `IncidentStatusUpdate`. |
| 26 | GET | `/inventory/products` | `list[MedicalSupplyResponse]` | **1. Ya serializado** | ORM separated; no nested relations. |
| 27 | POST | `/inventory/products` | `MedicalSupplyResponse` | **1. Ya serializado** | Input: `MedicalSupplyCreate`. |
| 28 | GET | `/inventory/products/{id}` | `MedicalSupplyResponse` | **1. Ya serializado** | |
| 29 | POST | `/inventory/orders/inbound` | `SupplyDeliveryResponse` | **1. Ya serializado** | Input: `SupplyDeliveryCreate`. |
| 30 | POST | `/inventory/orders/outbound` | `SupplyConsumptionResponse` | **1. Ya serializado** | Input: `SupplyConsumptionCreate`. |
| 31 | GET | `/inventory/orders` | `list[InventoryOrderListItem]` | **1. Ya serializado** | Lean history columns only. |

### Totals (milestone close)

| Classification | Count |
|----------------|-------|
| **1. Ya serializado** | **31** |
| **2. Parcialmente serializado** | **0** |
| **3. Sin serializar** | **0** |

Milestone gates:

- Every JSON endpoint has an explicit `response_model` → **pass**
- Write routes use separate input schemas → **pass**
- Auth register/login/forgot/reset never return password or email → **pass**
- `GET /auth/me` may return caller email → **pass**
- Runtime smoke + Postman checks match declared schemas → **pass**

---

## Target payloads (auth)

- `GET /auth/me` → `email`, `role`, `profile: ProfilePublic | null` (never `hashed_password`).
- `POST /users` → `RegisterResponse` without `email`.
- Password flows → `{ "message": "ok" }` only.
- Login → `access_token`, `token_type` only.

---

## Verification evidence

OpenAPI (`app.openapi()` / `/docs` / `/openapi.json`) lists an explicit JSON schema component for every JSON route above.  
`GET /api/incidents/results/export` is CSV `FileResponse` (no JSON body schema by design).  
`SupplierResponse` extends `SupplierBase` (not `SupplierCreate`).  
`RegisterResponse` properties: `id`, `is_active`, `role`, `created_at`.

Runtime checks (Docker rebuild on `feature/serialization-audit`, `http://127.0.0.1:8000`):

- Smoke: `POST /users` → no `email`; `POST /auth/login` → token only; `GET /auth/me` → caller `email` + profile; forgot/change-password → `{message}`; `GET /suppliers` → `SupplierResponse` rows; `GET /api/incidents` → lean list (no timestamps).
- Manual Postman: login then `GET /auth/me` with Bearer token; response shape matches `AuthMeResponse`.
