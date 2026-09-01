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

## Baseline (pre-milestone)

The **original state** below reflects `services/app/routers/` on `main` before branch `feature/serialization-audit` (reconstructed via `git show main:services/app/routers/<router>.py`).

After remediation, all **31** endpoints are **1. Ya serializado**. The master checklist documents before and after for each route.

---

## Master checklist

| # | Method | Path | Estado original | Schema original | Problema detectado | Estado actual | Schema actual | Notas |
|---|--------|------|-----------------|-----------------|-------------------|---------------|---------------|-------|
| 1 | POST | `/auth/login` | **1. Ya serializado** | `TokenResponse` | — | **1. Ya serializado** | `TokenResponse` | Sin cambio en este hito. Token only; no user/hash/email. |
| 2 | GET | `/auth/me` | **3. Sin serializar** | `(none)` — bare `dict` | No `response_model`; contrato implícito | **1. Ya serializado** | `AuthMeResponse` | Schema dedicado: `email`, `role`, `profile`. Caller email allowed for profile UI. |
| 3 | POST | `/auth/forgot-password` | **3. Sin serializar** | `(none)` — `JSONResponse` / dict | No `response_model`; cuerpo `{message}` sin schema | **1. Ya serializado** | `MessageResponse` | `{message}` only; no email echo. |
| 4 | POST | `/auth/reset-password` | **3. Sin serializar** | `(none)` — dict de servicio | No `response_model` | **1. Ya serializado** | `MessageResponse` | `{message}` only. |
| 5 | POST | `/auth/change-password` | **3. Sin serializar** | `(none)` — dict de servicio | No `response_model` | **1. Ya serializado** | `MessageResponse` | `{message}` only. |
| 6 | POST | `/users` | **2. Parcialmente serializado** | `UserPublic` | Devolvía `email`; input `UserCreate` aceptaba `role` | **1. Ya serializado** | `RegisterResponse` | `id`, `is_active`, `role`, `created_at` — **no email**. Input: `UserCreate` (no `role`). |
| 7 | GET | `/users` | **1. Ya serializado** | `list[UserPublic]` | — | **1. Ya serializado** | `list[UserPublic]` | Sin cambio en este hito. Lean public fields. |
| 8 | GET | `/users/{user_id}` | **1. Ya serializado** | `UserPublic` | — | **1. Ya serializado** | `UserPublic` | Sin cambio en este hito. |
| 9 | PUT | `/users/{user_id}` | **1. Ya serializado** | `UserPublic` | — | **1. Ya serializado** | `UserPublic` | Sin cambio en este hito. Input: `UserUpdate`; password write-only. |
| 10 | DELETE | `/users/{user_id}` | **3. Sin serializar** | `(none)` — `{"detail": "..."}` | No `response_model` | **1. Ya serializado** | `DetailResponse` | `{detail}`. |
| 11 | GET | `/profiles/me` | **1. Ya serializado** | `ProfilePublic` | — | **1. Ya serializado** | `ProfilePublic` | Sin cambio en este hito. |
| 12 | PUT | `/profiles/me` | **1. Ya serializado** | `ProfilePublic` | — | **1. Ya serializado** | `ProfilePublic` | Sin cambio en este hito. Input: `ProfileUpdate` (name/phone/address only). |
| 13 | POST | `/suppliers` | **2. Parcialmente serializado** | `Supplier` | `Supplier` hereda de `SupplierCreate` (lectura acoplada a escritura) | **1. Ya serializado** | `SupplierResponse` | Input: `SupplierCreate`; response does not inherit write validators. |
| 14 | GET | `/suppliers` | **2. Parcialmente serializado** | `list[Supplier]` | Mismo acoplamiento read/write | **1. Ya serializado** | `list[SupplierResponse]` | Full card fields (UI uses all). |
| 15 | GET | `/suppliers/{id}` | **2. Parcialmente serializado** | `Supplier` | Mismo acoplamiento read/write | **1. Ya serializado** | `SupplierResponse` | |
| 16 | PATCH | `/suppliers/{id}/rate` | **2. Parcialmente serializado** | `Supplier` | Mismo acoplamiento read/write | **1. Ya serializado** | `SupplierResponse` | Input: `SupplierRateUpdate`. |
| 17 | PATCH | `/suppliers/{id}/status` | **2. Parcialmente serializado** | `Supplier` | Mismo acoplamiento read/write | **1. Ya serializado** | `SupplierResponse` | Input: `SupplierStatusUpdate`. |
| 18 | DELETE | `/suppliers/{id}` | **3. Sin serializar** | `(none)` — `{"detail": "..."}` | No `response_model` | **1. Ya serializado** | `DetailResponse` | `{detail}`. |
| 19 | POST | `/api/incidents/analyze` | **3. Sin serializar** | `(none)` | No `response_model`; agregados sin contrato explícito | **1. Ya serializado** | `IncidentAnalysisSummary` | Aggregates only; no `patient_id` (PHI). |
| 20 | GET | `/api/incidents/results/export` | **1. Ya serializado** | `FileResponse` (CSV) | — | **1. Ya serializado** | `FileResponse` (CSV) | Sin cambio en este hito. Non-JSON file download; not an ORM dump. |
| 21 | GET | `/api/incidents/summary` | **1. Ya serializado** | `IncidentSummary` | — | **1. Ya serializado** | `IncidentSummary` | Sin cambio en este hito. |
| 22 | POST | `/api/incidents` | **1. Ya serializado** | `Incident` | — | **1. Ya serializado** | `Incident` | Sin cambio en este hito. Input: `IncidentCreate`. |
| 23 | GET | `/api/incidents` | **2. Parcialmente serializado** | `list[Incident]` | Listado con timestamps; payload más grande de lo necesario para la tabla UI | **1. Ya serializado** | `list[IncidentListItem]` | List without timestamps. |
| 24 | GET | `/api/incidents/{id}` | **1. Ya serializado** | `Incident` | — | **1. Ya serializado** | `Incident` | Sin cambio en este hito. Detail includes timestamps. |
| 25 | PATCH | `/api/incidents/{id}/status` | **1. Ya serializado** | `Incident` | — | **1. Ya serializado** | `Incident` | Sin cambio en este hito. Input: `IncidentStatusUpdate`. |
| 26 | GET | `/inventory/products` | **1. Ya serializado** | `list[MedicalSupplyResponse]` | — | **1. Ya serializado** | `list[MedicalSupplyResponse]` | Sin cambio en este hito. ORM separated; no nested relations. |
| 27 | POST | `/inventory/products` | **1. Ya serializado** | `MedicalSupplyResponse` | — | **1. Ya serializado** | `MedicalSupplyResponse` | Sin cambio en este hito. Input: `MedicalSupplyCreate`. |
| 28 | GET | `/inventory/products/{id}` | **1. Ya serializado** | `MedicalSupplyResponse` | — | **1. Ya serializado** | `MedicalSupplyResponse` | Sin cambio en este hito. |
| 29 | POST | `/inventory/orders/inbound` | **1. Ya serializado** | `SupplyDeliveryResponse` | — | **1. Ya serializado** | `SupplyDeliveryResponse` | Sin cambio en este hito. Input: `SupplyDeliveryCreate`. |
| 30 | POST | `/inventory/orders/outbound` | **1. Ya serializado** | `SupplyConsumptionResponse` | — | **1. Ya serializado** | `SupplyConsumptionResponse` | Sin cambio en este hito. Input: `SupplyConsumptionCreate`. |
| 31 | GET | `/inventory/orders` | **2. Parcialmente serializado** | `list[InventoryOrderResponse]` | Historial con campos extra (`supply_id`, `clinic_id`, etc.) no usados en la tabla UI | **1. Ya serializado** | `list[InventoryOrderListItem]` | Lean history columns only. |

### Totals — baseline (main, pre-milestone)

| Classification | Count | Endpoints |
|----------------|-------|-----------|
| **1. Ya serializado** | **16** | login; users GET/PUT; profiles; incidents summary/export/CRUD/detail/status; inventory products/inbound/outbound |
| **2. Parcialmente serializado** | **8** | `POST /users`; suppliers ×5; `GET /api/incidents`; `GET /inventory/orders` |
| **3. Sin serializar** | **7** | `GET /auth/me`; forgot/reset/change-password; `DELETE /users`; `DELETE /suppliers`; `POST /api/incidents/analyze` |

### Totals — post-milestone (current)

| Classification | Count |
|----------------|-------|
| **1. Ya serializado** | **31** |
| **2. Parcialmente serializado** | **0** |
| **3. Sin serializar** | **0** |

**15 endpoints remediated** in this milestone (7 unserialized + 8 partial). **16 endpoints** already met the bar on `main` and required no serializer change.

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
