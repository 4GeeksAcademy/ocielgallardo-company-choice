# Frontend Performance Audit — HealthCore

**Milestone:** Auditoría de Rendimiento Frontend (4Geeks Academy)  
**Baseline date:** 2026-08-25 (re-run, evening)  
**Environment:** local `next dev` (website `:3000`, backoffice `:3001`)  
**Evidence:** `audit/before/*.html`

> Phase 1 = measure & root-cause. Phase 2 code fixes are applied.  
> **After (2026-08-28):** 6/6 valid Lighthouse HTML in `audit/after/` (Docker prod, Incógnito). Deltas in `REPORT.md` §4.2.  
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

## 3. Core Web Vitals (baseline)

| Surface | Mode | FCP | LCP | TBT | CLS | TTFB |
|---------|------|-----|-----|-----|-----|------|
| Website `/` | Mobile | 1.7 s | **6.5 s** | **1,130 ms** | 0 | 80 ms |
| Website `/` | Desktop | 0.4 s | 1.2 s | 260 ms | 0 | 80 ms |
| Backoffice `/login` | Mobile | 0.8 s | 2.6 s | **2,390 ms** | 0 | 80 ms |
| Backoffice `/login` | Desktop | 0.4 s | 0.6 s | 530 ms | 0 | 70 ms |
| Backoffice `/` | Mobile | 1.2 s | **19.1 s** | **2,330 ms** | 0 | 70 ms |
| Backoffice `/` | Desktop | 0.4 s | **3.5 s** | 550 ms | 0 | 70 ms |

CLS and TTFB are healthy. LCP + TBT drive the Performance scores.

---

## 4. Problems — root cause

### P1 — Website LCP: unoptimized hero image

| | |
|--|--|
| **Where** | `HeroCarousel` — `/images/hero/hero-001.png` (~450 KiB PNG) via raw `<img>` |
| **Evidence** | LCP element = `.hero-carousel-image`; image-delivery ~**506–508 KiB** savings; no `fetchpriority` |
| **Root cause** | No `next/image`, large PNG, all slides eager |
| **Fix applied** | `next/image` + `fill` + `sizes="100vw"` + `priority` on first slide |

### P2 — Website a11y: focusable links inside `aria-hidden` mobile nav

| | |
|--|--|
| **Where** | `SiteHeader` closed mobile `<nav aria-hidden="true">` with live `<a>` / `<Link>` |
| **Evidence** | `aria-hidden-focus` failed (Accessibility 96) |
| **Root cause** | Menu kept in DOM for animation while closed, still tabbable |
| **Fix applied** | `tabIndex={-1}` on menu links when closed |

### P3 — Backoffice login: missing `<main>` landmark

| | |
|--|--|
| **Where** | Auth pages wrapped only in `<div>` |
| **Evidence** | `landmark-one-main` on `/login` |
| **Root cause** | Duplicated auth chrome without landmark |
| **Fix applied** | Shared `AuthPageShell` with `<main>` (login, register, forgot, reset) |

### P4 — Dashboard: heavy client JS / late LCP text paint

| | |
|--|--|
| **Where** | `/` loads `Hito2Playground` (client + domain utils) on critical path |
| **Evidence** | Dashboard mobile LCP **19.1 s**, TBT **2.3 s**; unused JS includes layout/login chunks in dev |
| **Root cause** | Eager client playground + `next dev` main-thread cost |
| **Fix applied** | `next/dynamic` for `Hito2Playground`; extended in P7 with viewport lazy wrapper |

### P5 — Render-blocking CSS / large payloads (both apps)

| | |
|--|--|
| **Evidence** | `layout.css` render-blocking; total weight ~3 MiB in places |
| **Root cause** | App Router CSS + assets; amplified in dev |
| **Status** | Partially helped by image optimization; full gain needs production build |

### P6 — Website `/application`: success feedback + redirect

| | |
|--|--|
| **Where** | `PatientApplicationForm.tsx`, `FormStatusMessage.tsx` |
| **Evidence** | Professor feedback: success state easy to miss; no redirect to home |
| **Root cause** | Inline `text-xs` status only; form reset on success obscured feedback |
| **Fix applied** | Full-screen success banner (`role="status"`), focus + scroll, redirect to `/` after 2 s; validation error banner on failed submit |

### P7 — Lazy viewport + code splitting (both UIs)

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
| Re-measure post-lazy (P7 delta vs current after) | TODO — optional; not run yet |
