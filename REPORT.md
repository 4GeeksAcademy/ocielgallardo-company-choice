# Informe de auditoría de rendimiento — HealthCore

**Hito:** Auditoría de Rendimiento Frontend (4Geeks Academy)  
**Rama:** `feature/performance-audit` (desde `main`)  
**Estado al 2026-08-28:** fixes aplicados + baseline + remeición after en Docker prod (6/6 HTML válidos — ver §4.2)

---

## 1. Resumen del progreso

| Paso | Estado |
|------|--------|
| Medición inicial (before) | Hecho — `audit/before/` (HTML + PNG) |
| Análisis y causa raíz | Hecho — `AUDIT.md` |
| Correcciones de código | Hecho — commits en esta rama |
| Componente reutilizable | Hecho — `AuthPageShell` |
| Remeición after | Hecho — `audit/after/` (6 HTML, Docker prod) |
| Cierre con deltas medibles | Hecho — ver §4.2 (caveat entorno before=dev / after=prod) |

---

## 2. Correcciones ya aplicadas

### F1 — Imágenes LCP (website)

- **Archivos:** `HeroCarousel.tsx`, `SiteHeader.tsx`, `globals.css`
- **Cambio:** `<img>` → `next/image` (hero con `fill` + `priority` en la primera slide; logo con width/height)
- **Motivo:** LCP móvil ~6.5 s y ~506 KiB ahorrables en entrega de imágenes

### F2 — Menú móvil `aria-hidden-focus` (website)

- **Archivo:** `SiteHeader.tsx`
- **Cambio:** `tabIndex={-1}` en enlaces del menú cuando está cerrado
- **Motivo:** Accessibility 96 por focuseables bajo `aria-hidden`

### F3 — `AuthPageShell` + `<main>` (backoffice)

- **Archivos:** `AuthPageShell.tsx` + login / register / forgot-password / reset-password
- **Cambio:** Chrome de auth compartido con landmark `<main>`
- **Motivo:** `landmark-one-main` en `/login`; cumple extracción de componente reutilizable

### F4 — Playground diferido (backoffice)

- **Archivo:** `app/page.tsx`
- **Cambio:** `Hito2Playground` con `next/dynamic`
- **Motivo:** Dashboard autenticado con LCP/TBT muy altos en baseline móvil

---

## 3. Puntuaciones baseline (before) — válidas

Evidencia: `audit/before/` (HTML + capturas PNG). Entorno: `next dev`.

### Website `/`

| Modo | Perf | A11y | BP | SEO |
|------|-----:|-----:|---:|----:|
| Mobile | 53 | 96 | 100 | 100 |
| Desktop | 88 | 96 | 100 | 100 |

### Backoffice `/login`

| Modo | Perf | A11y | BP | SEO |
|------|-----:|-----:|---:|----:|
| Mobile | 68 | 98 | 100 | 100 |
| Desktop | 78 | 98 | 100 | 100 |

### Backoffice `/` (dashboard autenticado)

| Modo | Perf | A11y | BP | SEO |
|------|-----:|-----:|---:|----:|
| Mobile | 46 | 100 | 100 | 100 |
| Desktop | 58 | 100 | 100 | 100 |

---

## 4. Remeición after

### 4.1 Primera pasada (2026-08-25) — descartada

Archivos en `audit/after/` de esa noche **no son evidencia oficial**: timeouts en móvil, IndexedDB/extensiones en desktop. Ver historial en `audit/after/README.md`.

### 4.2 Mediciones válidas (2026-08-28) — Docker producción

**Protocolo:** Chrome **Incógnito**, `docker compose up --build` (`next start` en UIs, uvicorn sin reload). Evidencia: `audit/after/*.html`.

**Caveat:** mediciones anteriores en `next dev` eran inestables (IndexedDB, `PROTOCOL_TIMEOUT`, scores &lt;49). Esta pasada completó las 6 corridas; si un valor parece anómalo, repetir en Incógnito limpio.

| Superficie | Modo | Perf | A11y | BP | SEO | Δ Perf | Archivo |
|------------|------|-----:|-----:|---:|----:|--------|---------|
| Website `/` | Mobile | **95** | 100 | 100 | 100 | **+42** | `website-mobil-test.html` |
| Website `/` | Desktop | **90** | 100 | 100 | 100 | **+2** | `website-desktop-test.html` |
| Backoffice `/login` | Mobile | **99** | 100 | 100 | 100 | **+31** | `backoffice-mobil-login-test.html` |
| Backoffice `/login` | Desktop | **100** | 100 | 100 | 100 | **+22** | `backoffice-desktop-login-test.html` |
| Backoffice `/` | Mobile | **95** | 100 | 100 | 100 | **+49** | `backoffice-mobil-test.html` |
| Backoffice `/` | Desktop | **100** | 100 | 100 | 100 | **+42** | `backoffice-desktop-test.html` |

**Interpretación:** todos los deltas de Performance son positivos. El salto más grande en dashboard/backoffice combina F4 (`next/dynamic`) con medir en **producción** vs baseline en `next dev`. Website mobile (+42) es el indicador más alineado con F1 (hero `next/image`).

Corridas con perfil normal (aviso **IndexedDB**) o `PROTOCOL_TIMEOUT` deben descartarse; Incógnito + Docker prod reducen ese ruido.

---

## 5. Qué tuvo (o debería tener) más impacto

| Prioridad | Fix | Por qué |
|-----------|-----|---------|
| 1 | Hero `next/image` + priority | Ataca LCP / bytes del website |
| 2 | `next/dynamic` del playground | Reduce JS crítico del dashboard |
| 3 | `AuthPageShell` + `tabIndex` menú | A11y + mantenibilidad |

---

## 6. Checklist restante

1. Opcional: capturas PNG en `audit/after/` para el entregable visual.
2. Abrir PR de `feature/performance-audit` → `main` cuando lo pidas.
3. Re-medir en Incógnito si alguna corrida futura falla o parece inconsistente.

Dev con hot reload: `npm run docker:dev`. Medición Lighthouse: `npm run docker:up` (prod default).

---

## 7. Commits relevantes en la rama

- `fa199de` — baseline + fixes de frontend  
- `e33172b` — capturas PNG before + regla `.cursor/rules/read-agents.mdc`  
- (este commit) — HTML after + documentación del checkpoint
