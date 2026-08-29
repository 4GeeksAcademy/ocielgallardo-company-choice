# Caching Optimisation Report — HealthCore Monorepo

**Branch:** `feature/caching-optimisation` (from `feature/performance-audit`)  
**Phase:** 5 — Backend TTL cache complete  
**Path:** [`docs/audit/CACHING_REPORT.md`](./CACHING_REPORT.md) (repo-root copy removed 2026-08-29)  
**Last updated:** 2026-08-29

---

## 1. Methodology

Caching decisions follow two axes (cost vs storage, freshness vs performance) and three filters (cost, frequency, stability). Session-scoped data must never use a shared cache key (HIPAA / UK GDPR).

### 1.5 Phase 2 measurement protocol

| Setting | Value |
|---------|--------|
| Tool | `scripts/measure_cache_candidates.py` (domain mode) |
| Iterations | 10 per endpoint |
| Volume seed | `scripts/seed_inventory_volume.py` |
| HTTP timing | `api.timing` middleware |

---

## 2. Data volume — before and after Phase 2 seed

| Store | Table | Before | After |
|-------|-------|--------|-------|
| Supabase | `medical_supplies` | 6 | 206 |
| Supabase | `supply_deliveries` | 8 | 4,008 |
| Supabase | `supply_consumptions` | 4 | 3,504 |

### 2.1 Measured latency — before cache (p50 ms, confirmed re-run 2026-08-28)

| Endpoint | Before seed | After seed | Cache? |
|----------|-------------|------------|--------|
| `/inventory/products` | 149.26 | **151.85** | Yes (Phase 5) |
| `/inventory/orders` | 197.79 | **363.74** | Yes (Phase 5) |
| `/api/incidents/summary` | 0.32 | 0.32 | No |
| `/suppliers` | 1.23 | 1.31 | No |

### 2.2 Measured latency — after Phase 5 cache (domain mode, n=10, 2026-08-29)

Same volume (206 / 4,008 / 3,504). First iteration is a cold miss; subsequent nine are hits. p50 therefore reflects **hit** cost; max approximates **miss**.

| Domain call | p50 (hit) | max (≈ miss) | Baseline p50 (Phase 2) |
|-------------|-----------|--------------|-------------------------|
| `list_supplies` → `GET /inventory/products` | **0.0 ms** | 322.87 ms | 151.85 ms |
| `list_orders` → `GET /inventory/orders` | **0.0 ms** | 732.72 ms | 363.74 ms |

Miss times vary with DB/network conditions; the important delta is hit ≈ **sub-millisecond** vs hundreds of ms of SQL + serialization work on every list refresh.

---

## 4. Frontend inventory

### 4.1 Baseline (backoffice)

| Location | Technique | Notes |
|----------|-----------|-------|
| `uis/backoffice/app/page.tsx` | `next/dynamic` | `Hito2Playground` |
| `uis/backoffice/app/incidents/*` | `next/dynamic` | Incident panels |
| `uis/backoffice/components/lazy/lazyViewportPanels.tsx` | `dynamic` + `LazyWhenVisible` | Suppliers, Inventory, Applications |

### 4.2 Phase 3 — website lazy loading (2026-08-28)

| File | Change |
|------|--------|
| `uis/website/components/lazy/lazyViewportSections.tsx` | `ServicesSectionLazy`, `ImpactSectionLazy`, `FinalCtaSectionLazy`, `SiteFooterLazy` |
| `uis/website/app/page.tsx` | Below-fold sections via lazy wrappers (separate JS chunks) |
| `uis/website/app/application/page.tsx` | `PatientApplicationForm` via `next/dynamic` |
| `uis/website/components/ui/createLazyViewportSection.tsx` | Types aligned with backoffice |

**Validation:** `cd uis/website && npm run build` — OK.

---

## 5. Frontend decisions (Phase 3 — implemented)

| Target | Technique | Justification |
|--------|-----------|---------------|
| Home below-fold sections | `createLazyViewportSection` | Not needed for first paint; static imports bundled all section JS upfront |
| `PatientApplicationForm` | `next/dynamic` | ~250-line client form; home `/` visitors do not need this chunk |

Backoffice lazy routes (§4.1) satisfy the ≥2 lazy-loading requirement together with website changes.

### 5.1 Phase 4 — `useMemo` (2026-08-29)

| Target | File | Dependencies | Why non-trivial |
|--------|------|--------------|-----------------|
| `orderSummary` | `uis/backoffice/components/inventory/InventoryOrdersList.tsx` | `[orders]` | Single-pass aggregate (counts + quantity totals by inbound/outbound) over the full API payload (~7.5k rows after volume seed) |
| `filteredOrders` | Same | `[orders, typeFilter]` | Client filter of the large list when the operator toggles type chips |
| `displayRows` | Same | `[filteredOrders]` | Maps visible rows and runs `toLocaleString` once per row; avoids re-formatting on every filter-button re-render |

**Estimated benefit:** With thousands of orders, changing the type filter or clicking “Actualizar” no longer re-aggregates and re-formats dates for the full list on unrelated re-renders. Aggregation stays O(n) only when `orders` changes; date formatting runs only when the filtered subset changes.

**Not used for this milestone:** trivial memos such as `token ?? null` or `Object.keys(errors).length` — they do not meet the “non-trivial calculation” bar.

---

## 6. Backend decisions (Phase 5 — implemented)

### 6.1 Endpoint evaluation (FastAPI surface)

| Endpoint | Cost | Call frequency | Data stability | Cache? |
|----------|------|----------------|----------------|--------|
| `POST /auth/login`, password flows | Crypto + TinyDB | Login bursts | N/A (writes/secrets) | **No** — credentials |
| `GET /auth/me` | TinyDB user | High (shell) | Per session | **No** — user-scoped; shared key = leak |
| `GET/PUT /profiles/me` | Profile row | Medium | Per user | **No** — same |
| `GET/POST/… /users*` | TinyDB | Admin-ish | User records | **No** — identity |
| `GET /suppliers` | TinyDB list | Medium (directory UI) | Changes on rate/status writes | **No** — p50 **1.31 ms**; cache adds complexity without benefit |
| `GET /api/incidents/summary` | In-memory aggregate | Medium | Changes on incident writes | **No** — p50 **0.32 ms** |
| `GET/POST /api/incidents*` (list/detail/analyze) | TinyDB / CSV | Variable | Frequent mutations | **No** — not Phase 2 bottleneck |
| `GET /inventory/products` | SQL + stock aggregates (~200 rows + joins) | High (products page, outbound form) | Changes only on product/inbound/outbound writes | **Yes** |
| `GET /inventory/orders` | Two large queries + merge/sort (~7.5k rows) | High (order history + refresh) | Same write set | **Yes** |
| `GET /inventory/products/{id}` | Single supply + stock | Low | Same | **No** — lower frequency; not a Phase 2 target |
| `POST /inventory/products`, `/orders/inbound`, `/orders/outbound` | Writes | Lower than GETs | Mutate lists/stock | **Invalidate** lists (not cached themselves) |

### 6.2 Cached endpoints

| Endpoint | Cache key | Cost (Phase 2 p50) | Est. frequency | TTL | Invalidation |
|----------|-----------|--------------------|----------------|-----|--------------|
| `GET /inventory/products` | `inventory:products` | **151.85 ms** | Products page load, outbound stock picker, manual refresh | **60 s** | `POST /inventory/products`, inbound, outbound |
| `GET /inventory/orders` | `inventory:orders` | **363.74 ms** | Order history page + “Actualizar” | **60 s** | inbound, outbound (and product create clears both) |

**Implementation:** in-process `TtlCache` in [`services/app/core/ttl_cache.py`](../../services/app/core/ttl_cache.py); wired in [`services/app/domain/inventory_service.py`](../../services/app/domain/inventory_service.py) (`list_supplies` / `list_orders` get+set; create paths call `_invalidate_inventory_lists()`).

**Why shared keys are safe:** both list handlers authenticate via `get_current_user` but **ignore** the user identity and return the org-wide catalog/history. They are not session or profile payloads. Auth still gates access; the cache does not mix private responses across users.

**Limit:** one dict per uvicorn worker. TTL covers the rare case of a missed invalidation or multi-worker lag until expiry.

### 6.3 Post-cache evidence

See §2.2: domain p50 hit **0.0 ms** for both lists after warm-up (2026-08-29). Smoke check: after `_invalidate_inventory_lists()`, both keys are empty and the next `list_supplies` rebuilds a new list object.

---

## 7. Freshness vs performance trade-off

**Choice:** TTL = **60 seconds**, with **immediate invalidation on every inventory write**.

- **Performance win:** repeated list reads (operators opening Historial / Suministros, or clicking Actualizar while data is unchanged) avoid re-running multi-thousand-row SQL and Python merge/sort. Measured hit cost collapses from hundreds of ms to ~0 ms in-process.
- **Freshness:** After a successful POST (new product, delivery, or consumption), both list keys are cleared in the same process, so the next GET rebuilds from the database. Operators who just registered a movement see updated stock and history without waiting for TTL.
- **Why 60 s is acceptable for this use case:** Inventory lists support clinic supply operations, not real-time clinical dosing or claims adjudication. The residual risk is only the edge case where invalidation does not run (crash mid-request, or another worker still holding a warm entry). In that edge case, a reader might see stock/history up to **one minute** stale — acceptable for educational/ops dashboards and far cheaper than paying ~364 ms on every poll. A shorter TTL (e.g. 5 s) would barely help multi-worker lag and would thrash the DB under refresh spam; a longer TTL (e.g. 10 min) without solid invalidation would be wrong for stock accuracy after outbound.

---

## 8. What will not be cached

| Endpoint / component | Reason |
|----------------------|--------|
| `GET /auth/me`, `GET /profiles/me` | Personalized; a shared key would leak identity/profile across users |
| `GET /suppliers` | Measured p50 **1.31 ms** — below the cost threshold; TinyDB list is already cheap |
| `GET /api/incidents/summary` | Measured p50 **0.32 ms** — no measurable win |
| `GET /inventory/products/{id}` | Considered; lower call frequency than list endpoints; Phase 2 bottleneck was the full lists |

---

## 9. Phase progress

- [x] Phase 1 — criteria, lifespan fix, initial report
- [x] Phase 2 — middleware, seed, measurements
- [x] Phase 3 — website lazy loading
- [x] Phase 4 — `useMemo` on inventory order history
- [x] Phase 5 — backend cache + TTL + invalidation

---

## 10. Validation checklist

| Requirement | Status |
|-------------|--------|
| ≥2 lazy-loaded routes with justification | **Done** (website + backoffice) |
| ≥1 non-trivial `useMemo` | **Done** — `InventoryOrdersList` (§5.1) |
| ≥2 cached endpoints with TTL | **Done** — products + orders, TTL 60 s (§6) |
| Cache invalidation on writes | **Done** — create supply/delivery/consumption |
| No private data on shared keys | **Done** — org-wide lists only; auth/me excluded (§8) |
| Explicit trade-off discussion | **Done** — §7 (60 s TTL) |
| Measured exclusion example | `/suppliers` 1.31 ms p50 |

---

## 11. Related fixes

- **Phase 1:** Removed duplicate `app = FastAPI()` (lifespan restored).
- **Phase 2:** Timing middleware; volume/measure scripts.
- **Phase 3:** Website `lazyViewportSections.tsx` and `/application` dynamic form.
- **Phase 4:** `InventoryOrdersList` — `orderSummary`, `filteredOrders`, `displayRows` via `useMemo`; `useAsyncQuery` effect no longer sync-setStates before await.
- **Phase 5:** `TtlCache` + inventory list caching/invalidation; post-cache domain timings in §2.2.
