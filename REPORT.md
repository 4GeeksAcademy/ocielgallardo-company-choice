# Performance Audit Report — HealthCore

**Milestone:** Auditoría de Rendimiento Frontend  
**Baseline evidence:** `audit/before/` (2026-08-25 re-run)  
**After evidence:** TODO — add HTML/screenshots under `audit/after/` after re-running Lighthouse on the same URLs

---

## 1. Fixes applied

### F1 — Optimize LCP images (website)

- **Files:** `uis/website/components/sections/HeroCarousel.tsx`, `uis/website/components/layout/SiteHeader.tsx`, `uis/website/app/globals.css`
- **Change:** Replaced raw `<img>` with `next/image`. Hero uses `fill` + `sizes="100vw"` and `priority` on the first slide. Logo uses fixed `width`/`height`.
- **Why:** Baseline image-delivery insight (~506 KiB) and LCP element were the hero PNG.
- **Expected impact:** Website Performance / LCP (especially mobile 6.5 s → closer to &lt; 2.5 s on optimized responses).

### F2 — Mobile nav `aria-hidden-focus` (website)

- **File:** `uis/website/components/layout/SiteHeader.tsx`
- **Change:** When the mobile menu is closed, links use `tabIndex={-1}` so they are not focusable under `aria-hidden="true"`.
- **Expected impact:** Accessibility 96 → 100 on website mobile/desktop.

### F3 — Shared `AuthPageShell` + `<main>` (backoffice)

- **Files:** `uis/backoffice/components/layout/AuthPageShell.tsx`; wired into `login`, `register`, `forgot-password`, `reset-password`
- **Change:** Extracted duplicated auth card chrome; root landmark is now `<main>`.
- **Expected impact:** Fixes `landmark-one-main` on `/login` (A11y 98 → 100). Satisfies the milestone “extract reusable component” requirement.

### F4 — Defer dashboard playground (backoffice)

- **File:** `uis/backoffice/app/page.tsx`
- **Change:** `Hito2Playground` loaded via `next/dynamic` with a lightweight loading placeholder.
- **Why:** Authenticated dashboard mobile had LCP **19.1 s** / TBT **2.3 s**; playground pulls client domain utilities onto the first paint path.
- **Expected impact:** Better dashboard Performance / TBT (largest gain in production build).

---

## 2. Baseline scores (before fixes)

### Website `/`

| Mode | Perf | A11y | BP | SEO |
|------|-----:|-----:|---:|----:|
| Mobile | 53 | 96 | 100 | 100 |
| Desktop | 88 | 96 | 100 | 100 |

### Backoffice `/login`

| Mode | Perf | A11y | BP | SEO |
|------|-----:|-----:|---:|----:|
| Mobile | 68 | 98 | 100 | 100 |
| Desktop | 78 | 98 | 100 | 100 |

### Backoffice `/` (dashboard)

| Mode | Perf | A11y | BP | SEO |
|------|-----:|-----:|---:|----:|
| Mobile | 46 | 100 | 100 | 100 |
| Desktop | 58 | 100 | 100 | 100 |

---

## 3. After scores (fill after re-measure)

| Surface | Mode | Perf | A11y | BP | SEO | Delta Perf |
|---------|------|-----:|-----:|---:|----:|------------|
| Website `/` | Mobile | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Website `/` | Desktop | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Backoffice `/login` | Mobile | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Backoffice `/login` | Desktop | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Backoffice `/` | Mobile | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Backoffice `/` | Desktop | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

Save new exports to `audit/after/` with clear names (e.g. `Website-mobile-test.html`).

---

## 4. What likely moved the needle most

| Rank | Fix | Why |
|------|-----|-----|
| 1 | Hero `next/image` + priority | Directly attacks website mobile LCP / image bytes |
| 2 | Dynamic `Hito2Playground` | Shrinks critical JS on the heaviest backoffice view |
| 3 | `AuthPageShell` + menu `tabIndex` | Accessibility wins; maintainability for auth UI |

---

## 5. How to validate (your next action)

1. Restart both apps (`npm run dev` in `uis/website` and `uis/backoffice`) so image optimization is active.
2. Re-run Lighthouse on the **same six** URL/mode combinations as baseline.
3. Drop HTML/screenshots into `audit/after/`.
4. Tell the agent (or edit this file) with the new four scores so §3 can be completed.

Optional stronger check: `npm run build && npm run start` then Lighthouse again (fairer than `next dev`).
