---
name: ui-ux-pro-max
description: "UI/UX design intelligence for web, mobile, and desktop. Use when designing, building, reviewing, or fixing interfaces, including pages, components, design systems, accessibility, interaction, responsive layout, typography, color, charts, and stack-specific UI implementation."
license: MIT
metadata:
  author: nextlevelbuilder
  version: "2.0"
---

# UI/UX Pro Max — Design Intelligence

Comprehensive design guide for web and mobile applications. Contains searchable database of UI styles, color palettes, font pairings, chart types, product recommendations, UX guidelines, and stack-specific best practices.

## Quick Start

### Generate Design System (REQUIRED for new projects)
Always start with `--design-system` to get comprehensive recommendations with reasoning:

```bash
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<product_type> <industry> <keywords>" --design-system [-p "Project Name"]
```

This command:
1. Searches 5 domains in parallel (product, style, color, landing, typography)
2. Applies reasoning rules from ui-reasoning.csv to select best matches
3. Returns complete design system: pattern, style, colors, typography, effects
4. Includes anti-patterns to avoid

Example:
```bash
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "saas dashboard minimal tech" --design-system -p "Leads CRM"
```

### Persist Design System (Master + Overrides Pattern)
To save the design system for hierarchical retrieval across sessions, add `--persist`:

```bash
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name"
```

This creates:
- `design-system/MASTER.md` — Global Source of Truth with all design rules
- `design-system/pages/` — Folder for page-specific overrides

With page-specific override:
```bash
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name" --page "dashboard"
```

This also creates:
- `design-system/pages/dashboard.md` — Page-specific deviations from Master

### Hierarchical Retrieval
1. When building a specific page (e.g., "Checkout"), first check `design-system/pages/checkout.md`
2. If the page file exists, its rules override the Master file
3. If not, use `design-system/MASTER.md` exclusively

---

## Search Reference

### Available Domains
| Domain | Focus | Examples |
|--------|-------|----------|
| `ux` | Best practices, anti-patterns | animation, accessibility, z-index, loading |
| `react` | React/Next.js performance | waterfall, bundle, suspense, memo, rerender, cache |
| `web` | Web interface guidelines | aria, focus, keyboard, semantic, virtualize |
| `prompt` | AI prompts, CSS keywords | (style name) |
| `style` | UI styles | glassmorphism, minimalism, brutalism |
| `color` | Color palettes | saas, healthcare, fintech |
| `typography` | Font pairings | elegant serif, modern sans |
| `chart` | Chart types | dashboard, analytics |
| `landing` | Landing patterns | hero social-proof, pricing |

### Available Stacks
| Stack | Focus |
|-------|-------|
| `html-tailwind` | Tailwind utilities, responsive, a11y (DEFAULT) |
| `react` | State, hooks, performance, patterns |
| `nextjs` | SSR, routing, images, API routes |
| `vue` | Composition API, Pinia, Vue Router |
| `svelte` | Runes, stores, SvelteKit |
| `swiftui` | Views, State, Navigation, Animation |
| `react-native` | Components, Navigation, Lists |
| `flutter` | Widgets, State, Layout, Theming |
| `shadcn` | shadcn/ui components, theming, forms, patterns |
| `jetpack-compose` | Composables, Modifiers, State Hoisting, Recomposition |

---

## Priority Rules (Must Follow)

| Priority | Category | Impact | Domain | Key Checks (Must Have) | Anti-Patterns (Avoid) |
|----------|----------|--------|--------|------------------------|----------------------|
| 1 | Accessibility | CRITICAL | ux | Contrast 4.5:1, Alt text, Keyboard nav, Aria-labels | Removing focus rings, Icon-only buttons without labels |
| 2 | Touch & Interaction | CRITICAL | ux | Min size 44×44px, 8px+ spacing, Loading feedback | Reliance on hover only, Instant state changes (0ms) |
| 3 | Performance | HIGH | ux | WebP/AVIF, Lazy loading, Reserve space (CLS < 0.1) | Layout thrashing, Cumulative Layout Shift |
| 4 | Style Selection | HIGH | style, product | Match product type, Consistency, SVG icons (no emoji) | Mixing flat & skeuomorphic randomly, Emoji as icons |
| 5 | Layout & Responsive | HIGH | ux | Mobile-first breakpoints, Viewport meta, No horizontal scroll | Horizontal scroll, Fixed px container widths, Disable zoom |
| 6 | Typography & Color | MEDIUM | typography, color | Base 16px, Line-height 1.5, Semantic color tokens | Text < 12px body, Gray-on-gray, Raw hex in components |
| 7 | Animation | MEDIUM | ux, gsap | Context-aware timing, Motion conveys meaning, Spatial continuity | One duration for every transition, Animating width/height, No reduced-motion |
| 8 | Forms & Feedback | MEDIUM | ux | Visible labels, Error near field, Helper text, Progressive disclosure | Placeholder-only label, Errors only at top, Overwhelm upfront |
| 9 | Navigation Patterns | HIGH | ux | Predictable back, Bottom nav ≤5, Deep linking | Overloaded nav, Broken back behavior, No deep links |
| 10 | Charts & Data | LOW | chart | Legends, Tooltips, Accessible colors | Relying on color alone to convey meaning |

For the full rule list per category (all 119 UX guidelines with rationale), see `references/quick-reference.md`.

For app-specific polish rules (icons, touch feedback, dark mode contrast, safe areas) and the canonical pre-delivery checklist, see `references/pro-rules.md`.

---

## Brand Integration (Leads CRM v1.2)

### Design Tokens from Brand Identity
```css
/* Brand Colors (from .agents/GallaDev_brand-identity/) */
--color-rojo: #C62828;        /* Identity / Accent (5-10%) */
--color-grafito: #1F2328;     /* Structure / Text (20-30%) */
--color-blanco: #FFFFFF;      /* Base / Space (60-70%) */

/* Neutrals */
--color-gris-claro: #F3F4F6;  /* Secondary backgrounds */
--color-gris-medio: #9CA3AF;  /* Secondary text, metadata */
--color-gris-oscuro: #4B5563; /* Subtitles, secondary nav */

/* Functional (NOT brand) */
--color-exito: #16A34A;
--color-advertencia: #D97706;
--color-error: #DC2626;
--color-info: #2563EB;
```

### Typography
- **Primary**: Manrope (Regular, Medium, Semibold, Bold)
- **Technical**: JetBrains Mono
- **Max families**: 2

### Motion
- **Base duration**: 150ms
- **Easing**: `cubic-bezier(0.4, 0, 0.2, 1)`
- **Respect**: `prefers-reduced-motion`

### Iconography
- **Functional**: Lucide Icons (outline, 24×24, stroke-2, round caps)
- **Brand microinteractions**: Gallo (loading: running, 400: pecking)

---

## Component Patterns for This Project

### Elevated shadcn/ui Components
| Component | Enhancement | Brand Adaptation |
|-----------|-------------|------------------|
| Button | Variants: primary(rojo), secondary(grafito), ghost, destructive | Rojo for primary CTAs |
| Card | Hover lift (150ms), shadow-md → shadow-lg | Grafito border, rojo accent on focus |
| Table | Virtualized, row hover lift, inline actions | Skeleton shimmer loading |
| Dialog | Framer-motion enter/exit, focus trap | Grafito bg, rojo focus ring |
| Select | Searchable, multi-select, virtualized options | Consistent with brand tokens |
| Toast (Sonner) | Progress variants, action buttons | Rojo error, verde success, azul info |

### New Components Needed
| Component | Reference | Priority |
|-----------|-----------|----------|
| KanbanBoard | Own framer-motion + 21st.dev patterns | P0 |
| DataTableVirtualized | TanStack Table + @tanstack/react-virtual | P0 |
| CommandPalette | ui-ux-pro-max pattern + 21st.dev | P1 |
| KPICard | 21st.dev Spotlight Card | P1 |
| StatCard | 21st.dev Display Cards | P2 |
| Skeleton | 21st.dev Skeleton shimmer | P1 |
| ProgressRing | Recharts/custom | P2 |
| SplitView | Custom | P2 |

---

## 21st.dev Reference Components

When requesting components, use these prompts:
```
"Create a [component] for a SaaS dashboard using:
- Tech: Next.js 16, React 19, Tailwind v4, shadcn/ui, framer-motion
- Brand: Minimal tech human — Rojo #C62828 (accent 5-10%), Grafito #1F2328, Manrope font
- Motion: 150ms base, cubic-bezier(0.4, 0, 0.2, 1), prefers-reduced-motion
- Style: Clean, professional, subtle motion — reference 21st.dev [component name]
- Accessibility: WCAG 2.2 AA, focus visible, keyboard nav, ARIA
- Dark mode: Full support via CSS variables"
```

### Specific References
- `Spotlight Card` → KPICard, StatCard
- `Display Cards` → Lead cards, Stat breakdowns
- `Scroll Choreography` → Home page sections
- `Container Scroll Animation` → Page transitions
- `Skeleton shimmer` → Loading states
- `Command Palette` → Global search
- `Tilt card` → Hover interactions (subtle)
- `Velaris` / `WaterRippleImage` → Hero/background effects

---

## Usage in This Project

### When to Use This Skill
- Designing new pages or components
- Refactoring existing UI for consistency
- Choosing colors, typography, spacing, layout systems
- Reviewing UI for UX/accessibility/consistency
- Implementing navigation, animation, responsive behavior
- Creating design system documentation

### Workflow
1. **Analyze requirements** → product type, industry, keywords
2. **Generate design system** → `--design-system --persist`
3. **Build components** → Follow MASTER.md + page overrides
4. **Review against rules** → Check priority table above
5. **Test accessibility** → Use `accessibility` skill for audit

---

## File Structure
```
.agents/skills/ui-ux-pro-max/
├── SKILL.md                    # This file
├── scripts/
│   └── search.py               # Design system generator
├── data/
│   ├── ui-styles.csv           # 67 styles
│   ├── color-palettes.csv      # 161 palettes
│   ├── font-pairings.csv       # 57 pairings
│   ├── chart-types.csv         # 25 types
│   ├── product-types.csv       # 161 types
│   ├── ux-guidelines.csv       # 119 guidelines
│   ├── ui-reasoning.csv        # Reasoning rules
│   └── landing-patterns.csv    # 34 patterns
└── references/
    ├── quick-reference.md      # All 119 rules with rationale
    └── pro-rules.md            # App-specific polish + checklist
```

---

## References
- [UI UX Pro Max Website](https://ui-ux-pro-max-skill.nextlevelbuilder.io/)
- [GitHub Repository](https://github.com/NextGenAILLC/ui-ux-pro-max-nextgenaillc)
- [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [21st.dev Components](https://21st.dev/)