# Backoffice UI/UX Improvement — Icons + Polish (No Rebranding)

Branch: `feature/backoffice-ui-ux` (cut from `main`).
Scope: `uis/backoffice` only. `uis/website` untouched.

## Objective

Give the internal backoffice a clearer, more scannable UI by adding a single
icon set and cleaning up small accessibility/dark-mode defects — without
changing brand tokens (palette, Inter, radii) or shell layout.

## What Changed

### Rules (governance)

- `.agents/rules/design.md` §11 — new operating rules for backoffice icons,
  navigation, states, dark mode, and the no-rebranding guardrail. Existing
  §§1–10 untouched.
- `.agents/rules/form-validation.md` — new single-responsibility rule for form
  validation UX (canonical `RegisterForm` pattern, per-field errors,
  `getFieldErrors()` API mapping, `useFormSubmit`, a11y).
- Note: no `docs/design.md` exists in this repo; per developer instruction the
  existing design rule file was extended instead of creating a new one.

### Backoffice (`uis/backoffice`)

- Dependency: `lucide-react` added (linear ~2px stroke, matches design §7;
  tree-shakable; icons render `aria-hidden="true"` with visible text labels).
- `components/layout/navConfig.ts` — `icon: LucideIcon` per group
  (+ `DASHBOARD_ICON`). Mapping: Dashboard `LayoutDashboard`, Incidents
  `Siren`, Suppliers `Truck`, Inventory `Boxes`, Telemetry `Activity`,
  People & Talent `Users`.
- `DesktopSidebar.tsx` — group + Dashboard links render 16px icons;
  `▾/▸` glyphs replaced with `ChevronDown`/`ChevronRight` (14px).
- `OfficeMenu.tsx` — same icons/chevrons in the mobile bottom sheet; removed
  duplicate `dark:text-*` on the panel header.
- `MobileBottomBar.tsx` — `LayoutDashboard` + `Building2` icons (18px) above
  labels; removed duplicate `dark:text-*` classes.
- `BackofficeShell.tsx` — logout keeps its label, now with leading `LogOut`
  icon (14px). `HC` badge and shell layout unchanged.
- `app/page.tsx` — dashboard `MODULES` cards render 18px icons
  (`Siren`, `ClipboardList`, `Truck`, `Boxes`, `PackageMinus`, `Users`);
  card chrome/hover unchanged.
- `ThemeToggle.tsx` — inline Sun/Moon SVGs replaced with lucide `Sun`/`Moon`
  (20px). Behavior unchanged.
- Duplicate-class cleanup (no visual change intended): `Input.tsx`,
  `Select.tsx` labels; `AccountMenu.tsx` button/menu/link classes;
  `Button.tsx` secondary variant (single `dark:border`/`dark:bg` each).

### Out of Scope (deliberately untouched)

- Palette, typography, radii, `md:pl-60` shell, routes, backend, telemetry
  events, `uis/website`, `company-choise.md`.
- Form logic migration to the new validation rule (Login/Supplier/inventory
  upgrades are a follow-up; rule is merged first so the pattern is agreed).

## Validation

- `npx tsc --noEmit` in `uis/backoffice`: clean.
- `npm run lint`: 16 problems (12 errors, 4 warnings) — identical count on
  clean `main` (verified via `git stash` baseline); all are pre-existing
  `react-hooks/set-state-in-effect` findings in untouched effects plus one
  unused-var warning in `telemetry.ts`. Zero new issues introduced.
- `npm run build`: blocked in this environment by Google Fonts TLS
  (`UNABLE_TO_VERIFY_LEAF_SIGNATURE` fetching `Inter` in `app/layout.tsx`) —
  same known limitation recorded for AUTH-03; unrelated to this change.

## Risks and Follow-ups

- `TODO:` Confirm canonical form locale (EN labels + ES hints vs full ES)
  before migrating forms to `form-validation.md`.
- `TODO:` Migrate `LoginForm` to per-field errors; retype `SupplierForm`
  `formStatus` as `{ kind, message }` (see rule).
- `TODO:` Manual pass in browser (light + dark, 360px + desktop,
  screen-reader check on `aria-current`/`role=alert`) — not run in this
  environment.
- `lucide-react` is a new runtime dependency (backoffice only).
