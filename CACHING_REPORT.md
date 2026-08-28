# Caching Optimisation Report — HealthCore Monorepo

**Branch:** `feature/caching-optimisation` (from `feature/performance-audit`)  
**Phase:** 2 — Measurement complete (middleware + volume seed + latency evidence)  
**Last updated:** 2026-08-28

---

## 1. Methodology

Caching decisions follow two axes (cost vs storage, freshness vs performance) and three filters (cost, frequency, stability). Session-scoped data must never use a shared cache key (HIPAA / UK GDPR).

### 1.5 Phase 2 measurement protocol

| Setting | Value |
|---------|--------|
| Tool | `scripts/measure_cache_candidates.py` (domain mode) |
| Iterations | 10 per endpoint |
| Reported stat | p50 (median), min, max (ms) |
| Volume seed | `scripts/seed_inventory_volume.py` (+200 supplies, +4000 deliveries, +3500 consumptions) |
| HTTP timing | `api.timing` middleware in `services/app/main.py` |

---

## 2. Data volume — before and after Phase 2 seed

| Store | Table | Before | After |
|-------|-------|--------|-------|
| Supabase | `medical_supplies` | 6 | 206 |
| Supabase | `supply_deliveries` | 8 | 4,008 |
| Supabase | `supply_consumptions` | 4 | 3,504 |
| TinyDB | `incidents` | 95 | 95 |
| TinyDB | `suppliers` | 16 | 16 |

### 2.1 Measured latency (domain layer, p50 ms)

| Endpoint | Before p50 | After p50 (confirmed re-run) | Cost filter (after) |
|----------|------------|------------------------------|---------------------|
| `/inventory/products` | 149.26 | **151.85** | **Pass** |
| `/inventory/orders` | 197.79 | **363.74** | **Pass** (strongest) |
| `/api/incidents/summary` | 0.32 | 0.32 | **Fail** |
| `/suppliers` | 1.23 | 1.31 | **Fail** |

Full samples (ms):

| Target | Before min / p50 / max | After min / p50 / max |
|--------|------------------------|------------------------|
| `inventory_products` | 145.11 / 149.26 / 157.10 | 146.83 / 151.85 / 238.87 |
| `inventory_orders` | 191.56 / 197.79 / 220.23 | 339.12 / 363.74 / 518.41 |
| `incidents_summary` | 0.30 / 0.32 / 2.06 | 0.29 / 0.32 / 0.52 |
| `suppliers_list` | 1.23 / 1.23 / 5.76 | 1.23 / 1.31 / 2.70 |

---

## 3.7 Confirmed backend shortlist (Phase 5)

1. **`GET /inventory/orders`** — p50 **364 ms** after volume seed.
2. **`GET /inventory/products`** — p50 **152 ms**; high UI frequency.

**Excluded after measurement:** `/api/incidents/summary` (0.32 ms), `/suppliers` (1.31 ms).

---

## 4. Frontend inventory (baseline)

Backoffice already uses `next/dynamic` (incidents, lazy panels). Website home still uses static imports + `LazyWhenVisible` only — **Phase 3**.

---

## 6. Backend decisions (Phase 5 targets)

| Endpoint | Before p50 | After p50 | Invalidation |
|----------|------------|-----------|--------------|
| `GET /inventory/orders` | 197.79 ms | **363.74 ms** | POST inbound/outbound |
| `GET /inventory/products` | 149.26 ms | **151.85 ms** | POST products/inbound/outbound |

---

## 7. Trade-offs

- **`/inventory/orders`:** Brief staleness on history list acceptable; invalidate on writes.
- **`/inventory/products`:** List may be briefly stale; outbound POST remains authoritative on stock.

---

## 8. What will not be cached

| Endpoint | Reason |
|----------|--------|
| `GET /auth/me`, `GET /profiles/me` | Cross-user leak risk |
| `GET /suppliers` | **Measured p50 1.31 ms** — no measurable gain |
| `GET /api/incidents/summary` | **Measured p50 0.32 ms** |

---

## 9. Phase 2 — completed / Phase 3 — next

- [x] Timing middleware, volume seed, benchmark script
- [x] Latency tables in this report
- [ ] Website lazy loading (Phase 3)

---

## 11. Related fixes

- **Phase 1:** Removed duplicate `app = FastAPI()` (lifespan restored).
- **Phase 2:** `api.timing` middleware; `scripts/seed_inventory_volume.py`; `scripts/measure_cache_candidates.py`.
