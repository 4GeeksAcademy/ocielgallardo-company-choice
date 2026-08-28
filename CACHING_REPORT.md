# Caching Optimisation Report — HealthCore Monorepo

**Branch:** `feature/caching-optimisation` (from `feature/performance-audit`)  
**Phase:** 3 — Frontend lazy loading complete (website); Phase 4 (useMemo) next  
**Last updated:** 2026-08-28

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

### 2.1 Measured latency (p50 ms, confirmed re-run 2026-08-28)

| Endpoint | Before | After | Cache? |
|----------|--------|-------|--------|
| `/inventory/products` | 149.26 | **151.85** | Yes (Phase 5) |
| `/inventory/orders` | 197.79 | **363.74** | Yes (Phase 5) |
| `/api/incidents/summary` | 0.32 | 0.32 | No |
| `/suppliers` | 1.23 | 1.31 | No |

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

---

## 6. Backend decisions (Phase 5 — targets from Phase 2)

| Endpoint | After p50 | Invalidation |
|----------|-----------|--------------|
| `GET /inventory/orders` | **363.74 ms** | POST inbound/outbound |
| `GET /inventory/products` | **151.85 ms** | POST products/inbound/outbound |

---

## 8. What will not be cached

| Endpoint | Reason |
|----------|--------|
| `GET /auth/me`, `GET /profiles/me` | Cross-user leak |
| `GET /suppliers` | p50 **1.31 ms** |
| `GET /api/incidents/summary` | p50 **0.32 ms** |

---

## 9. Phase progress

- [x] Phase 1 — criteria, lifespan fix, initial report
- [x] Phase 2 — middleware, seed, measurements
- [x] Phase 3 — website lazy loading
- [ ] Phase 4 — `useMemo`
- [ ] Phase 5 — backend cache + TTL

---

## 10. Validation checklist

| Requirement | Status |
|-------------|--------|
| ≥2 lazy-loaded routes with justification | **Done** (website + backoffice) |
| ≥1 non-trivial `useMemo` | Phase 4 |
| ≥2 cached endpoints with TTL | Phase 5 |
| Explicit trade-off discussion | §6–§7 |
| Measured exclusion example | `/suppliers` 1.31 ms p50 |

---

## 11. Related fixes

- **Phase 1:** Removed duplicate `app = FastAPI()` (lifespan restored).
- **Phase 2:** Timing middleware; volume/measure scripts.
- **Phase 3:** Website `lazyViewportSections.tsx` and `/application` dynamic form.
