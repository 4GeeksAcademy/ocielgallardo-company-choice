# Caching Optimisation Report — HealthCore Monorepo

**Branch:** `feature/caching-optimisation` (from `feature/performance-audit`)
**Phase:** 1 — Criteria and baseline inventory (no measurement or cache implementation yet)
**Last updated:** 2026-08-28

---

## 1. Methodology

Caching decisions follow two axes (cost vs storage, freshness vs performance) and three filters (cost, frequency, stability). Session-scoped data must never use a shared cache key (HIPAA / UK GDPR).

See full endpoint inventory and frontend baseline in subsequent commits (Phases 2–3).

---

## 2. Current data volume (baseline)

| Store | Table / collection | Approx. rows |
|-------|-------------------|--------------|
| Supabase | `medical_supplies` | 6 |
| Supabase | movements | Seed only |
| TinyDB | `incidents` | ~95 |
| TinyDB | `suppliers` | 16 |

Phase 2 will add volume seed and latency measurements.

---

## 8. What will not be cached (initial exclusions)

| Endpoint | Reason |
|----------|--------|
| `GET /auth/me` | User-specific; shared key = cross-user leak |
| `GET /profiles/me` | PII per user |
| `GET /suppliers` | Expected low cost at current volume (re-evaluate after Phase 2) |

---

## 9. Phase 2 plan (next)

- HTTP timing middleware
- `scripts/seed_inventory_volume.py` and `scripts/measure_cache_candidates.py`
- Update this report with measured latencies

---

## 11. Related fixes (Phase 1)

- **`services/app/main.py`:** Removed duplicate `app = FastAPI(...)` that overwrote `lifespan`.
