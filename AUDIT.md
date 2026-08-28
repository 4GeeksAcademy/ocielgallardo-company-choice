# Frontend Performance Audit — HealthCore

**Milestone:** Auditoría de Rendimiento Frontend (4Geeks Academy)  
**Baseline date:** 2026-08-25 (re-run, evening)  
**Environment:** local `next dev` (website `:3000`, backoffice `:3001`)  
**Evidence:** `audit/before/*.html`

> Phase 1 = measure & root-cause. Phase 2 code fixes are applied.  
> **After (2026-08-28):** 6/6 valid Lighthouse HTML in `audit/after/` (Docker prod, Incógnito) — **pre-P7 lazy** (before commit `17b0d6e`). Deltas in `REPORT.md` §4.2.  
> **Final (post-P7):** pending — save 6 HTML in `audit/final/` per `audit/final/README.md`; fill `REPORT.md` §4.3.  
> **Phase 3 (2026-08-28):** UX form success, backoffice extractions, lazy viewport — see P6/P7 below (commit `17b0d6e`).

---

## 1. What was measured (baseline)

| App | URL | Modes | Source file |
|-----|-----|-------|-------------|
| Website | `http://localhost:3000/` | Mobile + Desktop | `Website-mobile-test.html`, `Website-Desktop-test.html` |
| Backoffice auth | `http://localhost:3001/login` | Mobile + Desktop | `Backoffice-mobile-test.html`, `Backoffice-Desktop-test.html` |
| Backoffice app | `http://localhost:3001/` (authenticated) | Mobile + Desktop | `Backoffice-insite-mobile-test.html`, `Backoffice-insite-desktop-test.html` |

### Caveats

1. Measured on **`next dev`** — TBT / unused JS are inflated vs production.
2. Prefer a clean Chrome profile (extensions can skew Best Practices / unused JS).
3. Website sample is home only. TODO: optional `/application` pass if required by instructor.

---

## 2. Baseline Lighthouse scores

### Website — `/`

| Mode | Performance | Accessibility | Best Practices | SEO |
|------|-------------:|--------------:|---------------:|----:|
| Mobile | **53** | 96 | 100 | 100 |
| Desktop | **88** | 96 | 100 | 100 |

### Backoffice — `/login`

| Mode | Performance | Accessibility | Best Practices | SEO |
|------|-------------:|--------------:|---------------:|----:|
| Mobile | **68** | 98 | 100 | 100 |
| Desktop | **78** | 98 | 100 | 100 |

### Backoffice — `/` (dashboard, logged in)

| Mode | Performance | Accessibility | Best Practices | SEO |
|------|-------------:|--------------:|---------------:|----:|
| Mobile | **46** | 100 | 100 | 100 |
| Desktop | **58** | 100 | 100 | 100 |

**Verdict:** A11y / BP / SEO are strong. Performance is the gap — worst on website mobile (53) and dashboard mobile (46).

---

## 3. Core Web Vitals (KPI-first)

Extracted with `node scripts/extract-lighthouse-kpis.mjs … --markdown`.  
\* **INP:** `interaction-to-next-paint` when present in the export; otherwise **maxPotentialFID** (lab proxy — common in Lighthouse 13.x HTML).

### 3.0 Baseline (`audit/before/` — `next dev`)

| Surface | Mode | Perf | FCP | LCP | INP* | TBT | CLS | TTFB |
|---------|------|-----:|-----|-----|------|-----|----:|------|
| Website `/` | Mobile | 53 | 1.7 s | **6.5 s** | **2,280 ms** | **1,130 ms** | 0 | 80 ms |
| Website `/` | Desktop | 88 | 0.4 s | 1.2 s | 570 ms | 260 ms | 0 | 80 ms |
| Backoffice `/login` | Mobile | 68 | 0.8 s | 2.6 s | **2,430 ms** | **2,390 ms** | 0 | 80 ms |
| Backoffice `/login` | Desktop | 78 | 0.4 s | 0.6 s | 580 ms | 530 ms | 0 | 70 ms |
| Backoffice `/` | Mobile | 46 | 1.2 s | **19.1 s** | **2,380 ms** | **2,330 ms** | 0 | 70 ms |
| Backoffice `/` | Desktop | 58 | 0.4 s | **3.5 s** | 600 ms | 550 ms | 0 | 70 ms |

### 3.0.1 After 2026-08-28 (`audit/after/` — Docker prod, **pre-P7**)

| Surface | Mode | Perf | FCP | LCP | INP* | TBT | CLS | TTFB |
|---------|------|-----:|-----|-----|------|-----|----:|------|
| Website `/` | Mobile | 95 | 0.8 s | 3.0 s | 90 ms | 20 ms | 0 | ~0 ms |
| Website `/` | Desktop | 90 | 0.2 s | 0.7 s | 20 ms | 0 ms | 0 | ~0 ms |
| Backoffice `/login` | Mobile | 99 | 0.8 s | 2.1 s | 90 ms | 40 ms | 0 | ~10 ms |
| Backoffice `/login` | Desktop | 100 | 0.2 s | 0.5 s | 20 ms | 0 ms | 0 | ~10 ms |
| Backoffice `/` | Mobile | 95 | 0.8 s | 2.9 s | 110 ms | 60 ms | 0 | ~0 ms |
| Backoffice `/` | Desktop | 100 | 0.2 s | 0.7 s | 20 ms | 0 ms | 0 | ~0 ms |

### 3.0.2 Final post-P7 (`audit/final/` — TODO)

| Surface | Mode | Perf | FCP | LCP | INP* | TBT | CLS | TTFB |
|---------|------|-----:|-----|-----|------|-----|----:|------|
| *(6 surfaces)* | — | TODO | TODO | TODO | TODO | TODO | TODO | TODO |

Run protocol in `audit/final/README.md`, then `node scripts/extract-lighthouse-kpis.mjs audit/final/*.html --markdown` and update `REPORT.md` §4.3.

### 3.1 KPI interpretation order

When reading Lighthouse (lab) or field data, prioritize in this order:

1. **TTFB** — server / network baseline (healthy here; not the bottleneck).
2. **LCP** — largest contentful paint; primary load KPI (P1 hero, P4/P7 deferral).
3. **CLS** — layout stability (already 0 across surfaces).
4. **INP** — interaction responsiveness (field KPI; lab proxy via INP* column above).
5. **TBT** — lab main-thread blocking; complements INP when field INP is unavailable.
6. **Performance score** — composite; useful for summary, not for root-cause alone.

**Secondary (outside perf KPI scope for this milestone):** Accessibility (P2, P3), Best Practices, SEO — strong baselines; fixes applied but not the performance gap.

---

## 4. Problems — root cause

### P1 — Website LCP: unoptimized hero image `KPI`

| | |
|--|--|
| **Where** | `HeroCarousel` — `/images/hero/hero-001.png` (~450 KiB PNG) via raw `<img>` |
| **Evidence** | LCP element = `.hero-carousel-image`; image-delivery ~**506–508 KiB** savings; no `fetchpriority` |
| **Root cause** | No `next/image`, large PNG, all slides eager |
| **Fix applied** | `next/image` + `fill` + `sizes="100vw"` + `priority` on first slide |

### P2 — Website a11y: focusable links inside `aria-hidden` mobile nav `Secondary (Lighthouse A11y)`

| | |
|--|--|
| **Where** | `SiteHeader` closed mobile `<nav aria-hidden="true">` with live `<a>` / `<Link>` |
| **Evidence** | `aria-hidden-focus` failed (Accessibility 96) |
| **Root cause** | Menu kept in DOM for animation while closed, still tabbable |
| **Fix applied** | `tabIndex={-1}` on menu links when closed |

### P3 — Backoffice login: missing `<main>` landmark `Secondary (Lighthouse A11y)`

| | |
|--|--|
| **Where** | Auth pages wrapped only in `<div>` |
| **Evidence** | `landmark-one-main` on `/login` |
| **Root cause** | Duplicated auth chrome without landmark |
| **Fix applied** | Shared `AuthPageShell` with `<main>` (login, register, forgot, reset) |

### P4 — Dashboard: heavy client JS / late LCP text paint `KPI`

| | |
|--|--|
| **Where** | `/` loads `Hito2Playground` (client + domain utils) on critical path |
| **Evidence** | Dashboard mobile LCP **19.1 s**, TBT **2.3 s**; unused JS includes layout/login chunks in dev |
| **Root cause** | Eager client playground + `next dev` main-thread cost |
| **Fix applied** | `next/dynamic` for `Hito2Playground`; extended in P7 with viewport lazy wrapper |

### P5 — Render-blocking CSS / large payloads (both apps) `KPI`

| | |
|--|--|
| **Evidence** | `layout.css` render-blocking; total weight ~3 MiB in places |
| **Root cause** | App Router CSS + assets; amplified in dev |
| **Status** | Partially helped by image optimization; full gain needs production build |

### P6 — Website `/application`: success feedback + redirect `UX (outside perf KPI)`

| | |
|--|--|
| **Where** | `PatientApplicationForm.tsx`, `FormStatusMessage.tsx` |
| **Evidence** | Professor feedback: success state easy to miss; no redirect to home |
| **Root cause** | Inline `text-xs` status only; form reset on success obscured feedback |
| **Fix applied** | Full-screen success banner (`role="status"`), focus + scroll, redirect to `/` after 2 s; validation error banner on failed submit |

### P7 — Lazy viewport + code splitting (both UIs) `KPI`

| | |
|--|--|
| **Where** | `LazyWhenVisible.tsx`, `createLazyViewportPanel` / `createLazyViewportSection`; website home sections + footer; backoffice dashboard playground, workspaces, incident/inventory panels |
| **Evidence** | Below-fold sections and heavy client panels loaded eagerly on initial paint |
| **Root cause** | No intersection-based deferral; workspace chunks in main route bundle |
| **Fix applied** | `IntersectionObserver` (`rootMargin: 200px`) + `next/dynamic` for below-fold / heavy panels; hero and page headers remain eager |

---

## 5. Refactor candidates (milestone)

| Case | Before | Abstraction |
|------|--------|-------------|
| Auth page chrome | Duplicated on 4 pages | **`AuthPageShell`** (implemented) |
| Form field + errors | Repeated across auth forms | **`FormMessage`** + **`useFormSubmit`** (implemented — auth forms) |
| Async list states | Suppliers / incidents / inventory | **`useAsyncQuery`** + **`AsyncRequestPanel`** (implemented — inventory/incidents panels) |

---

## 6. Phase checklist

| Item | Status |
|------|--------|
| Baseline Lighthouse (website + backoffice login + dashboard) | Done — `audit/before/` |
| Root-cause analysis | Done — this file |
| Targeted fixes (images, a11y, shared shell, dynamic import) | Done — code |
| Re-measure → `audit/after/` + score delta in `REPORT.md` | Done — `audit/after/README.md` (2026-08-28) |
| UX + lazy viewport (P6, P7) + backoffice extractions | Done — commit `17b0d6e` |
| KPI extraction script + `audit/final/` protocol | Done — `scripts/extract-lighthouse-kpis.mjs`, `audit/final/README.md` |
| Final Lighthouse pass post-P7 (`audit/final/` → `REPORT.md` §4.3) | **Pending user** — see `audit/final/README.md` |
