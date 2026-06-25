---
name: Clinical Intelligence System
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf3'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e6eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d5e3fc'
  on-surface: '#0d1c2e'
  on-surface-variant: '#434655'
  inverse-surface: '#233144'
  inverse-on-surface: '#eaf1ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#4059aa'
  on-secondary: '#ffffff'
  secondary-container: '#8fa7fe'
  on-secondary-container: '#1d3989'
  tertiary: '#005a82'
  on-tertiary: '#ffffff'
  tertiary-container: '#0074a6'
  on-tertiary-container: '#e4f2ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#dce1ff'
  secondary-fixed-dim: '#b6c4ff'
  on-secondary-fixed: '#00164e'
  on-secondary-fixed-variant: '#264191'
  tertiary-fixed: '#c9e6ff'
  tertiary-fixed-dim: '#89ceff'
  on-tertiary-fixed: '#001e2f'
  on-tertiary-fixed-variant: '#004c6e'
  background: '#f8f9ff'
  on-background: '#0d1c2e'
  surface-variant: '#d5e3fc'
  success: '#22c55e'
  warning: '#f59e0b'
  danger: '#dc2626'
  info: '#06b6d4'
  surface-bg: '#f8fafc'
  surface-border: '#e2e8f0'
  text-primary: '#1e293b'
  text-secondary: '#475569'
  high-contrast: '#020617'
typography:
  headline-display:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '800'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1280px
  form-max: 1024px
  gutter: 24px
  margin-mobile: 16px
  section-v: 56px
---

## Brand & Style

The design system is engineered for **HealthCore Digital**, prioritizing clinical precision, human empathy, and high-density data utility. The target audience includes clinicians, healthcare administrators, and patients who require immediate clarity without the "clinical anxiety" typically associated with medical software.

The visual style is **Corporate Modern with Glassmorphic accents**. It utilizes a systematic approach to density, ensuring that predictive healthcare data is readable and actionable. The interface feels "airy" through the use of generous whitespace and blurred background layers, but remains grounded by a structured slate-based neutral palette. This balance ensures the product feels like a reliable medical tool while maintaining a contemporary, approachable user experience.

**Key Principles:**
- **Clarity over Decoration:** Every element must serve a functional purpose in the clinical workflow.
- **Data-Dense Utility:** Dashboards prioritize information density through optimized typography and compact components.
- **Empathetic Precision:** Softened shapes and optimistic imagery offset the coldness of data-heavy interfaces.
- **Predictive Visibility:** Risk levels are color-coded to provide immediate cognitive shortcuts for decision-making.

## Colors

The palette is built on a foundation of **Trust (Blues)** and **Clarity (Slates)**. The primary blue (`#2563eb`) is used for action-oriented elements, while the deep indigo-blue (`#1e3a8a`) provides structural hierarchy. 

**Semantic Usage:**
- **Success (`green-500`):** Positive outcomes, completed tasks, and stable health metrics.
- **Warning (`amber-500`):** Pending actions or low-to-medium predictive risk.
- **Danger (`red-600`):** Critical alerts or high-risk thresholds (>70%). Use sparingly to avoid "alarm fatigue."
- **Info (`cyan-500`):** System guidance and supplementary medical information.

**Accessibility:** All text and icon combinations must meet **WCAG AA** standards. Use `slate-800` for primary body text on `slate-50` backgrounds to ensure maximum legibility.

## Typography

This design system exclusively uses **Inter** to ensure maximum legibility across dense data tables and complex medical forms. Inter’s tall x-height and neutral character make it ideal for high-density interfaces.

**Usage Guidelines:**
- **Headlines:** Use `ExtraBold` for landing pages and `Bold/SemiBold` for internal dashboard modules.
- **Body:** The default body size is `16px` with a `1.5` line height to maintain readability during long-form clinical reviews.
- **Labels:** Small labels (`12px`) should use `SemiBold` or `Medium` weights to remain legible even at reduced sizes.
- **Alignment:** Numbers in data tables should use tabular figures (mono-spacing for digits) where possible to facilitate vertical comparison of patient metrics.

## Layout & Spacing

The system employs a **Fluid Grid** model that adapts from a single column on mobile to a multi-column dashboard on desktop.

**Breakpoints & Grids:**
- **Desktop (1280px+):** 12-column grid. Dashboards may use a 3-5 column widget layout.
- **Tablet (768px - 1279px):** 2-column layout for main content areas.
- **Mobile (<768px):** Single-column stack with `16px` side margins.

**Spacing Rhythm:**
A strict 4px/8px-based spacing scale is used. Landing sections utilize `56px` (py-14) vertical padding to provide visual breathing room. Internal application workspaces should use more compact padding (e.g., `16px` to `24px`) to increase the "above-the-fold" data density.

## Elevation & Depth

Visual hierarchy is established through **Tonal Layers** and subtle **Glassmorphism**.

- **Backgrounds:** Use `slate-50` for the base canvas. Workspace "tiles" or "cards" use a white background to pop against the base.
- **Shadows:** Cards use a "Sombra Suave" (soft shadow): `0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)`.
- **Glassmorphism:** Navigation headers and central Hero overlays must use a background blur (`backdrop-filter: blur(8px)`) with a semi-transparent white fill (`rgba(255, 255, 255, 0.8)`).
- **Interactions:** Use a subtle lifting effect (`hover:-translate-y-1`) for interactive cards to provide tactile feedback without cluttering the UI.
- **Focus States:** Every interactive element must utilize a `2px` ring offset with a `primary-600` focus ring for WCAG compliance.

## Shapes

The shape language is **Rounded**, moving away from sharp clinical corners to foster a sense of modern care.

- **Buttons & Small Inputs:** `8px` (lg) radius.
- **Standard Cards:** `12px` (xl) radius.
- **Major Sections/Containers:** `16px` (2xl) radius.
- **Status Badges & Tags:** Full "Pill" radius for immediate distinction from actionable buttons.
- **Borders:** Consistent `1px` weight using `slate-200`.

## Components

**Buttons:**
- **Primary:** `primary-600` background, white text. `8px` radius.
- **Secondary:** `slate-50` background, `slate-800` text, `slate-200` border.
- **Critical:** `red-600` background. Reserved for destructive actions.

**Predictive Visualization:**
- **Probability Bars:** Horizontal bars representing risk levels. Transition color to `red-600` automatically when values exceed 70%. Below 70%, use `primary-600` or `amber-500` based on the specific medical context.
- **KPI Widgets:** Large `headline-lg` numeric values with small `label-sm` trend indicators (up/down arrows) placed to the right.

**Input Fields:**
- Default state: `1px` border in `slate-200`.
- Focus state: `2px` ring in `primary-600` with `2px` white offset.
- Error state: `1px` border in `red-600` with supporting error text in `red-600`.

**Navigation:**
- **Sticky Header:** Glassmorphic effect with a bottom border of `slate-200`.
- **Footer:** High-contrast `slate-950` background with `slate-400` text for legal and secondary links.

**Iconography:**
- Use **Linear/Outline** icons with a `2px` stroke weight. Icons should be sized to `20px` or `24px` within standard UI components. Use `primary-600` for active states.