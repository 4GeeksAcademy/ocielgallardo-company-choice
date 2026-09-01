# Performance audit — HealthCore

Evidencia y documentación del hito **Auditoría de Rendimiento Frontend** (4Geeks Academy), más el informe del hito de **caching**.

**Location:** `docs/audit/` (moved from repo-root `audit/` on 2026-08-29; `CACHING_REPORT.md` moved here from the repo root at the same time).
# Audits — HealthCore

Evidencia y documentación de auditorías técnicas (4Geeks Academy).

## Serialization audit (API)

| Documento | Contenido |
|-----------|-----------|
| [`serialization-audit.md`](./serialization-audit.md) | **Milestone complete** — 31/31 endpoints Ya serializado; before/after checklist per endpoint (baseline on `main`), target payloads, smoke/Postman evidence |

Status: closed on branch `feature/serialization-audit`. Every JSON route declares an explicit Pydantic `response_model`; auth register/login/forgot/reset never echo password or email (`GET /auth/me` may return caller email). Baseline: 16 OK / 8 partial / 7 unserialized on `main`; 15 routes remediated in this milestone.

## Performance audit (frontend)

| Documento | Contenido |
|-----------|-----------|
| [`AUDIT.md`](./AUDIT.md) | Causa raíz (P1–P7), tablas KPI, checklist |
| [`REPORT.md`](./REPORT.md) | Informe en español, deltas, notas PR |
| [`CACHING_REPORT.md`](./CACHING_REPORT.md) | Optimización de caching (frontend + backend) |

## Evidencia Lighthouse

| Carpeta | Cuándo | Entorno |
|---------|--------|---------|
| [`before/`](./before/) | Baseline 2026-08-25 | `next dev` |
| [`after/`](./after/) | 2026-08-28, pre-P7 lazy | Docker prod |
| [`final/`](./final/) | 2026-08-28, post-P7 | Docker prod |

Extraer métricas (desde la raíz del monorepo):

```bash
node scripts/extract-lighthouse-kpis.mjs docs/audit/<pass>/*.html --markdown
```
Extraer métricas: `node scripts/extract-lighthouse-kpis.mjs docs/audit/<pass>/*.html --markdown`
