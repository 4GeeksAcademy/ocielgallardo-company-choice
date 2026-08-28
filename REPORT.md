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
| Componente reutilizable | Hecho — ver §1.1 |
| Remeición after | Hecho — `audit/after/` (6 HTML, Docker prod) |
| Cierre con deltas medibles | Parcial — §4.2 (before→after pre-P7); §4.3 pendiente post-P7 |

### 1.1 Componentes y hooks reutilizables (hito)

| Abstracción | Uso |
|-------------|-----|
| **`AuthPageShell`** | Chrome compartido auth backoffice con `<main>` |
| **`FormMessage`** | Mensajes de error/éxito en formularios auth |
| **`useFormSubmit`** | Submit async + estados loading/error en auth forms |
| **`useAsyncQuery`** | Fetch con loading/error para listas async |
| **`AsyncRequestPanel`** | UI loading/error/empty unificada (incidents, inventory) |
| **`LazyWhenVisible`** | `IntersectionObserver` + placeholder (website + backoffice) |
| **`FormStatusMessage`** | Banner éxito/error en formulario website `/application` |

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

### F5 — Formulario website: éxito + redirect (P6)

- **Archivos:** `PatientApplicationForm.tsx`, `FormStatusMessage.tsx`, `app/application/page.tsx`
- **Cambio:** Banner de éxito visible, focus/scroll, redirección a `/` tras 2 s; banner de error en validación
- **Motivo:** Feedback del profesor en `/application`; UX de intake clara

### F6 — Lazy viewport + code splitting (P7)

- **Archivos:** `LazyWhenVisible.tsx`, `createLazyViewportPanel.tsx`, `createLazyViewportSection.tsx`; páginas home/workspaces/incidents/inventory
- **Cambio:** `IntersectionObserver` + `next/dynamic` para secciones below-the-fold y paneles pesados
- **Motivo:** Reducir JS y render inicial; cargar contenido al acercarse al viewport

### F7 — Extracciones backoffice (refactors)

- **Archivos:** `FormMessage.tsx`, `useFormSubmit.ts`, `useAsyncQuery.ts`, `AsyncRequestPanel.tsx`; forms auth + paneles async
- **Cambio:** Mensajes de formulario y estados loading/error unificados
- **Motivo:** Mantenibilidad; cierra candidatos de refactor del hito (§5 `AUDIT.md`)

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

### 4.3 Final post-P7 (`audit/final/`) — pendiente

**Estado:** carpeta y protocolo listos (`audit/final/README.md`); HTML aún no subidos.  
**Cuándo medir:** tras `docker compose up --build` con rama actual (incluye P7 lazy, commit `17b0d6e`+).

#### Tabla KPI (rellenar tras pasada)

| Superficie | Modo | Perf | LCP | INP* | CLS | TTFB | TBT | Archivo |
|------------|------|-----:|-----|------|----:|------|-----|---------|
| Website `/` | Mobile | TODO | TODO | TODO | TODO | TODO | TODO | `website-mobil-test.html` |
| Website `/` | Desktop | TODO | TODO | TODO | TODO | TODO | TODO | `website-desktop-test.html` |
| Backoffice `/login` | Mobile | TODO | TODO | TODO | TODO | TODO | TODO | `backoffice-mobil-login-test.html` |
| Backoffice `/login` | Desktop | TODO | TODO | TODO | TODO | TODO | TODO | `backoffice-desktop-login-test.html` |
| Backoffice `/` | Mobile | TODO | TODO | TODO | TODO | TODO | TODO | `backoffice-mobil-test.html` |
| Backoffice `/` | Desktop | TODO | TODO | TODO | TODO | TODO | TODO | `backoffice-desktop-test.html` |

Extraer filas: `node scripts/extract-lighthouse-kpis.mjs audit/final/*.html --markdown`

\* INP: audit `interaction-to-next-paint` o maxPotentialFID (proxy lab).

#### Δ vs baseline (`audit/before/`) — mejora total del hito

| Superficie | Modo | Δ Perf | Δ LCP | Δ INP* | Δ TBT | Notas |
|------------|------|--------|-------|--------|-------|-------|
| *(6 filas)* | — | TODO | TODO | TODO | TODO | Comparar final vs §3.0 `AUDIT.md` |

#### Δ vs after 2026-08-28 (`audit/after/`, pre-P7) — impacto F5–F7

| Superficie | Modo | Δ Perf | Δ LCP | Δ INP* | Δ TBT | Notas |
|------------|------|--------|-------|--------|-------|-------|
| *(6 filas)* | — | TODO | TODO | TODO | TODO | Aísla P6 UX + P7 lazy vs pasada pre-lazy |

---

## 5. Qué tuvo (o debería tener) más impacto

| Prioridad | Fix | Por qué |
|-----------|-----|---------|
| 1 | Hero `next/image` + priority | Ataca LCP / bytes del website |
| 2 | `next/dynamic` del playground | Reduce JS crítico del dashboard |
| 3 | `AuthPageShell` + `tabIndex` menú | A11y + mantenibilidad |
| 4 | Lazy viewport (F6) | Diferir chunks below-the-fold; menor TBT/JS en carga inicial (sin delta Lighthouse post-P7 aún) |
| 5 | Form success `/application` (F5) | UX / feedback profesor; impacto perf marginal |

---

## 6. Checklist restante

1. **Usuario:** 6 HTML en `audit/final/` + rellenar §4.3 (dual delta vs before y vs after).
2. Opcional: capturas PNG en `audit/after/` para el entregable visual.
3. Abrir PR de `feature/performance-audit` → `main` cuando lo pidas.
4. Re-medir en Incógnito si alguna corrida futura falla o parece inconsistente.

Dev con hot reload: `npm run docker:dev`. Medición Lighthouse: `npm run docker:up` (prod default).

---

## 8. Notas para PR

Los fixes del hito se agruparon en commits por fase (baseline + correcciones core, stack Docker prod, UX/lazy + extracciones backoffice, documentación), no en el formato “un fix = un commit + Lighthouse cada vez”. La evidencia Lighthouse sigue el protocolo batch: baseline en `next dev` (`audit/before/`), remeición válida en Docker prod (`audit/after/`, 2026-08-28, **antes** de P7 lazy), y pasada **final** post-P7 pendiente en `audit/final/`.

En el análisis se priorizan **KPIs de rendimiento** (TTFB → LCP → CLS → INP → TBT → Performance score) sobre categorías secundarias de Lighthouse (A11y/BP/SEO), que ya partían de puntuaciones altas. P1/P4/P5/P7 son KPI; P2/P3 son secundarias Lighthouse; P6 es UX fuera del alcance perf KPI.

Script de extracción: `scripts/extract-lighthouse-kpis.mjs`. Tablas maestras: `AUDIT.md` §3.

---

## 7. Commits relevantes en la rama

- `fa199de` — baseline + fixes de frontend  
- `e33172b` — capturas PNG before + regla `.cursor/rules/read-agents.mdc`  
- `af71d60` — merge main (depuración / dark mode)  
- `e974475` — Docker prod stack por defecto  
- `0affcaf` — HTML after + deltas Lighthouse en `REPORT.md`  
- `17b0d6e` — form success website, extracciones backoffice, lazy viewport  
- `24a6e0b` — docs P6/P7 + a11y lazy placeholders
- *(pendiente)* — docs KPI/INP, `audit/final/`, script extracción Lighthouse
