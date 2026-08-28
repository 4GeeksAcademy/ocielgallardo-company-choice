# Mediciones after

## Primera pasada (2026-08-25) — descartada

Archivos eliminados (`Website-mobile-test.html`, `Backoffice-mobile-test.html`, etc.): `PROTOCOL_TIMEOUT` en móvil, aviso IndexedDB en desktop con perfil no Incógnito. No usar como delta.

## Segunda pasada (2026-08-28) — Docker producción

**Protocolo:** Chrome **Incógnito**, stack `docker compose up --build` (`next start` + uvicorn sin reload), rama `feature/performance-audit`.

**Caveat:** el entorno local sigue siendo algo inestable — en algunas corridas previas el informe no cargaba bien o la puntuación variaba mucho (`next dev`, IndexedDB, timeouts). Estos 6 HTML completaron sin `PROTOCOL_TIMEOUT` ni `runWarnings`; conviene re-medir si un score parece anómalo.

### Puntuaciones (extraídas de HTML en esta carpeta)

| Superficie | Modo | Perf | A11y | BP | SEO | Δ Perf vs before | Archivo |
|------------|------|-----:|-----:|---:|----:|-----------------:|---------|
| Website `/` | Mobile | **95** | 100 | 100 | 100 | **+42** (53→95) | `website-mobil-test.html` |
| Website `/` | Desktop | **90** | 100 | 100 | 100 | **+2** (88→90) | `website-desktop-test.html` |
| Backoffice `/login` | Mobile | **99** | 100 | 100 | 100 | **+31** (68→99) | `backoffice-mobil-login-test.html` |
| Backoffice `/login` | Desktop | **100** | 100 | 100 | 100 | **+22** (78→100) | `backoffice-desktop-login-test.html` |
| Backoffice `/` (auth) | Mobile | **95** | 100 | 100 | 100 | **+49** (46→95) | `backoffice-mobil-test.html` |
| Backoffice `/` (auth) | Desktop | **100** | 100 | 100 | 100 | **+42** (58→100) | `backoffice-desktop-test.html` |

Baseline: `audit/before/` medido en `next dev`. After: Docker prod local.

**Nota metodológica:** comparar before (`next dev`) con after (Docker `next start`) mezcla **fix de código** y **cambio de entorno**. Los deltas son válidos como evidencia del hito, pero el salto grande en backoffice dashboard refleja sobre todo dejar de medir en dev.

Tabla resumen y checklist: `REPORT.md` §4.2.
