#!/usr/bin/env python3
"""
UI/UX Pro Max — Design System Generator
Searches design database and generates comprehensive design system recommendations.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# ─── Configuration ──────────────────────────────────────────────────────────
SKILL_ROOT = Path(__file__).parent.parent
DATA_DIR = SKILL_ROOT / "data"
OUTPUT_DIR = Path.cwd() / "design-system"

# ─── Mock Data (replace with actual CSV loading) ────────────────────────────
STYLES = [
    {"name": "Minimalism", "keywords": ["clean", "simple", "professional", "tech"], "compatible_stacks": ["react", "nextjs", "shadcn"]},
    {"name": "Glassmorphism", "keywords": ["modern", "transparent", "blur"], "compatible_stacks": ["react", "nextjs"]},
    {"name": "Brutalism", "keywords": ["bold", "raw", "unconventional"], "compatible_stacks": ["react", "nextjs"]},
    {"name": "Dark Mode", "keywords": ["dark", "night", "low-light"], "compatible_stacks": ["all"]},
]

COLOR_PALETTES = [
    {"name": "SaaS Professional", "primary": "#2563EB", "secondary": "#64748B", "accent": "#0EA5E9", "background": "#FFFFFF", "text": "#1E293B", "industry": ["saas", "tech", "dashboard"]},
    {"name": "Minimal Tech", "primary": "#1F2328", "secondary": "#4B5563", "accent": "#C62828", "background": "#FFFFFF", "text": "#1F2328", "industry": ["tech", "minimal", "developer-tools"]},
]

FONT_PAIRINGS = [
    {"name": "Manrope + JetBrains Mono", "heading": "Manrope", "body": "Manrope", "code": "JetBrains Mono", "mood": ["professional", "technical", "clean"]},
]

CHART_TYPES = [
    {"name": "Line Chart", "use_case": "trends over time", "library": "Recharts"},
    {"name": "Bar Chart", "use_case": "comparisons", "library": "Recharts"},
    {"name": "Sparkline", "use_case": "inline trends", "library": "Recharts"},
]

LANDING_PATTERNS = [
    {"name": "Hero + Features", "structure": ["hero", "features", "social-proof", "cta"], "cta_placement": "hero + footer"},
    {"name": "Video-First", "structure": ["hero-video", "benefits", "demo", "pricing"], "cta_placement": "hero + sticky"},
]

UX_GUIDELINES = [
    {"category": "Accessibility", "rule": "Contrast 4.5:1 minimum for text", "priority": "CRITICAL"},
    {"category": "Touch", "rule": "Minimum 44x44px touch targets", "priority": "CRITICAL"},
    {"category": "Performance", "rule": "CLS < 0.1, lazy load images", "priority": "HIGH"},
    {"category": "Animation", "rule": "Respect prefers-reduced-motion", "priority": "MEDIUM"},
]

# ─── Core Functions ─────────────────────────────────────────────────────────

def search_styles(query: str) -> List[Dict]:
    """Search styles matching query keywords."""
    keywords = query.lower().split()
    results = []
    for style in STYLES:
        score = sum(1 for kw in keywords if kw in style["keywords"])
        if score > 0:
            results.append({**style, "score": score})
    return sorted(results, key=lambda x: x["score"], reverse=True)[:3]

def search_colors(query: str) -> List[Dict]:
    """Search color palettes matching query."""
    keywords = query.lower().split()
    results = []
    for palette in COLOR_PALETTES:
        score = sum(1 for kw in keywords if kw in palette["industry"])
        if score > 0:
            results.append({**palette, "score": score})
    return sorted(results, key=lambda x: x["score"], reverse=True)[:3]

def search_typography(query: str) -> List[Dict]:
    """Search font pairings matching query."""
    keywords = query.lower().split()
    results = []
    for pairing in FONT_PAIRINGS:
        score = sum(1 for kw in keywords if kw in pairing["mood"])
        if score > 0:
            results.append({**pairing, "score": score})
    return sorted(results, key=lambda x: x["score"], reverse=True)[:2]

def search_charts(query: str) -> List[Dict]:
    """Search chart types matching query."""
    keywords = query.lower().split()
    results = []
    for chart in CHART_TYPES:
        score = sum(1 for kw in keywords if kw in chart["use_case"])
        if score > 0:
            results.append({**chart, "score": score})
    return sorted(results, key=lambda x: x["score"], reverse=True)[:3]

def search_landing(query: str) -> List[Dict]:
    """Search landing patterns matching query."""
    keywords = query.lower().split()
    results = []
    for pattern in LANDING_PATTERNS:
        score = sum(1 for kw in keywords if any(kw in s for s in pattern["structure"]))
        if score > 0:
            results.append({**pattern, "score": score})
    return sorted(results, key=lambda x: x["score"], reverse=True)[:2]

def get_ux_guidelines() -> List[Dict]:
    """Return all UX guidelines."""
    return UX_GUIDELINES

def generate_design_system(
    query: str,
    project_name: str,
    page: Optional[str] = None,
    stack: str = "shadcn"
) -> Dict:
    """Generate complete design system from query."""
    
    styles = search_styles(query)
    colors = search_colors(query)
    typography = search_typography(query)
    charts = search_charts(query)
    landing = search_landing(query)
    guidelines = get_ux_guidelines()
    
    # Brand-specific overrides for Leads CRM
    brand_override = {
        "colors": {
            "primary": "#C62828",      # Rojo GallaDev
            "secondary": "#1F2328",    # Grafito
            "accent": "#C62828",
            "background": "#FFFFFF",
            "text": "#1F2328",
            "muted": "#9CA3AF",
            "border": "#E5E7EB",
            "functional": {
                "success": "#16A34A",
                "warning": "#D97706",
                "error": "#DC2626",
                "info": "#2563EB"
            }
        },
        "typography": {
            "heading": "Manrope",
            "body": "Manrope",
            "code": "JetBrains Mono",
            "weights": ["400", "500", "600", "700"],
            "scale": {
                "xs": "0.75rem", "sm": "0.875rem", "base": "1rem",
                "lg": "1.125rem", "xl": "1.25rem", "2xl": "1.5rem",
                "3xl": "1.875rem", "4xl": "2.25rem"
            }
        },
        "motion": {
            "base_duration": "150ms",
            "easing": "cubic-bezier(0.4, 0, 0.2, 1)",
            "reduced_motion": True
        },
        "spacing": {"base": "4px", "scale": [4, 8, 12, 16, 20, 24, 32, 40, 48, 64]},
        "radius": {"sm": "4px", "md": "8px", "lg": "12px", "xl": "16px", "full": "9999px"},
        "shadows": {
            "sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
            "md": "0 4px 6px -1px rgb(0 0 0 / 0.1)",
            "lg": "0 10px 15px -3px rgb(0 0 0 / 0.1)",
            "xl": "0 20px 25px -5px rgb(0 0 0 / 0.1)",
            "glow_primary": "0 0 20px -5px rgb(198 40 40 / 0.4)"
        }
    }
    
    return {
        "project": project_name,
        "page": page,
        "stack": stack,
        "query": query,
        "style": styles[0] if styles else STYLES[0],
        "color_palette": colors[0] if colors else COLOR_PALETTES[1],  # Minimal Tech
        "typography": typography[0] if typography else FONT_PAIRINGS[0],
        "charts": charts,
        "landing_pattern": landing[0] if landing else LANDING_PATTERNS[0],
        "ux_guidelines": guidelines,
        "brand_override": brand_override,
        "anti_patterns": [
            "Mixing flat & skeuomorphic randomly",
            "Emoji as icons (use Lucide SVG)",
            "Raw hex colors in components (use semantic tokens)",
            "Text < 12px for body",
            "Gray-on-gray low contrast",
            "One duration for every transition",
            "Animating width/height (use transform)",
            "No reduced-motion support",
            "Placeholder-only labels",
            "Errors only at top of form",
            "Horizontal scroll on mobile",
            "Fixed px container widths",
            "Disable zoom"
        ]
    }

def write_master(ds: Dict, project_name: str) -> Path:
    """Write MASTER.md design system file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    master_path = OUTPUT_DIR / "MASTER.md"
    
    content = f"""# Design System — {project_name}

**Generated from:** `{ds['query']}`
**Stack:** {ds['stack']}
**Page override:** {ds['page'] or 'None (global)'}

---

## 1. Visual Style

**Primary Style:** {ds['style']['name']}
**Keywords:** {', '.join(ds['style']['keywords'])}

---

## 2. Color Palette

### Brand Colors (Override)
| Role | Hex | Usage |
|------|-----|-------|
| Primary | `{ds['brand_override']['colors']['primary']}` | CTAs, primary actions, brand identity |
| Secondary | `{ds['brand_override']['colors']['secondary']}` | Text, structure, navigation |
| Accent | `{ds['brand_override']['colors']['accent']}` | Highlights, focus rings, active states |
| Background | `{ds['brand_override']['colors']['background']}` | Page backgrounds, cards |
| Text | `{ds['brand_override']['colors']['text']}` | Primary text content |
| Muted | `{ds['brand_override']['colors']['muted']}` | Secondary text, placeholders |
| Border | `{ds['brand_override']['colors']['border']}` | Borders, dividers |

### Functional Colors
| Role | Hex | Usage |
|------|-----|-------|
| Success | `{ds['brand_override']['colors']['functional']['success']}` | Positive states, confirmations |
| Warning | `{ds['brand_override']['colors']['functional']['warning']}` | Caution, pending states |
| Error | `{ds['brand_override']['colors']['functional']['error']}` | Errors, destructive actions |
| Info | `{ds['brand_override']['colors']['functional']['info']}` | Information, help |

### Proportions (Brand Guideline)
- **60-70%** → Background + light neutrals
- **20-30%** → Secondary (Grafito) for structure
- **5-10%** → Primary (Rojo) for accent/identity

---

## 3. Typography

| Role | Font | Weights |
|------|------|---------|
| Heading | {ds['brand_override']['typography']['heading']} | {', '.join(ds['brand_override']['typography']['weights'])} |
| Body | {ds['brand_override']['typography']['body']} | {', '.join(ds['brand_override']['typography']['weights'][:2])} |
| Code | {ds['brand_override']['typography']['code']} | 400, 500 |

### Scale
```css
{chr(10).join(f'--text-{k}: {v};' for k, v in ds['brand_override']['typography']['scale'].items())}
```

---

## 4. Motion

| Property | Value |
|----------|-------|
| Base Duration | {ds['brand_override']['motion']['base_duration']} |
| Easing | {ds['brand_override']['motion']['easing']} |
| Reduced Motion | {ds['brand_override']['motion']['reduced_motion']} |

### Presets
- **Micro** (100ms): Hover, focus
- **Base** (150ms): Default transitions, drag, expand
- **Macro** (200-300ms): Page transitions, modals
- **Count-up** (800-1200ms): KPI counters
- **Stagger** (50ms delay): List items

---

## 5. Spacing & Layout

**Base Unit:** {ds['brand_override']['spacing']['base']}
**Scale:** {ds['brand_override']['spacing']['scale']}

### Border Radius
```css
{chr(10).join(f'--radius-{k}: {v};' for k, v in ds['brand_override']['radius'].items())}
```

### Shadows
```css
{chr(10).join(f'--shadow-{k}: {v};' for k, v in ds['brand_override']['shadows'].items())}
```

---

## 6. Recommended Charts

{chr(10).join(f'- **{c["name"]}** ({c["use_case"]}) → {c["library"]}' for c in ds['charts'])}

---

## 7. Landing Pattern (if applicable)

**Pattern:** {ds['landing_pattern']['name']}
**Structure:** {' → '.join(ds['landing_pattern']['structure'])}
**CTA Placement:** {ds['landing_pattern']['cta_placement']}

---

## 8. UX Guidelines (Priority Order)

{chr(10).join(f'{i+1}. **{g["category"]}** ({g["priority"]}): {g["rule"]}' for i, g in enumerate(ds['ux_guidelines']))}

---

## 9. Anti-Patterns (Avoid)

{chr(10).join(f'- {ap}' for ap in ds['anti_patterns'])}

---

## 10. Component Inventory

### Current (shadcn/ui)
- Button, Dialog, Input, Switch

### Target (Elevated + New)
| Component | Source | Priority | Brand Notes |
|-----------|--------|----------|-------------|
| KanbanBoard | Own + framer-motion | P0 | 9 cols, Rojo drag line |
| DataTableVirtualized | TanStack + virtual | P0 | Row hover lift |
| CommandPalette | ui-ux-pro-max pattern | P1 | Cmd+K global search |
| KPICard | 21st.dev Spotlight | P1 | Count-up, sparkline |
| StatCard | 21st.dev Display Cards | P2 | Micro-chart |
| Skeleton | 21st.dev Shimmer | P1 | Gallo runner |
| Toast | Sonner extended | P1 | Progress, variants |
| ProgressRing | Recharts/custom | P2 | Inbox queues |
| SplitView | Custom | P2 | Email editor/preview |

---

## 11. 21st.dev Reference Components

- `Spotlight Card` → KPICard, StatCard
- `Display Cards` → Lead cards, Stat breakdowns
- `Scroll Choreography` → Home page sections
- `Container Scroll Animation` → Page transitions
- `Skeleton shimmer` → Loading states
- `Command Palette` → Global search
- `Tilt card` → Subtle hover interactions
- `Velaris` / `WaterRippleImage` → Hero effects

---

## 12. Accessibility (WCAG 2.2 AA)

- [ ] Contrast 4.5:1 (verify Rojo on Grafito)
- [ ] Focus visible: `focus-visible:ring-2 focus-visible:ring-rojo`
- [ ] Keyboard nav: Tab order, Escape, Arrow keys
- [ ] ARIA labels on icon buttons
- [ ] Live regions for dynamic content
- [ ] Reduced motion respected
- [ ] Skip links
- [ ] Target size ≥ 44×44px

---

*Generated by ui-ux-pro-max skill*
"""
    
    master_path.write_text(content, encoding="utf-8")
    return master_path

def write_page_override(ds: Dict, page: str) -> Path:
    """Write page-specific override file."""
    pages_dir = OUTPUT_DIR / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_path = pages_dir / f"{page}.md"
    
    content = f"""# Page Override — {page}

**Extends:** MASTER.md
**Project:** {ds['project']}

---

## Page-Specific Deviations

*Add page-specific overrides here. These take precedence over MASTER.md.*

### Layout
- 

### Components
- 

### Colors
- 

### Motion
- 

### Content
- 

---

*Edit this file to customize {page} without affecting global design system.*
"""
    
    page_path.write_text(content, encoding="utf-8")
    return page_path

# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UI/UX Pro Max — Design System Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 search.py "saas dashboard minimal tech" --design-system -p "MyApp"
  python3 search.py "saas dashboard minimal tech" --design-system --persist -p "MyApp" --page "dashboard"
  python3 search.py "fintech app" --design-system --persist -p "FinApp" --stack shadcn
        """
    )
    
    parser.add_argument("query", help="Product type, industry, style keywords (e.g., 'saas dashboard minimal tech')")
    parser.add_argument("--design-system", action="store_true", help="Generate full design system (required)")
    parser.add_argument("--persist", action="store_true", help="Persist to design-system/ folder")
    parser.add_argument("-p", "--project", default="Project", help="Project name")
    parser.add_argument("--page", help="Page-specific override (e.g., 'dashboard', 'checkout')")
    parser.add_argument("--stack", default="shadcn", choices=["html-tailwind", "react", "nextjs", "vue", "svelte", "shadcn"], help="Target stack")
    
    args = parser.parse_args()
    
    if not args.design_system:
        parser.error("--design-system is required. Use --design-system to generate.")
    
    print(f"[SEARCH] Searching for: {args.query}")
    print(f"[PROJECT] Project: {args.project}")
    print(f"[STACK] Stack: {args.stack}")
    if args.page:
        print(f"[PAGE] Page override: {args.page}")
    
    ds = generate_design_system(args.query, args.project, args.page, args.stack)
    
    if args.persist:
        master_path = write_master(ds, args.project)
        print(f"[OK] Created: {master_path}")
        
        if args.page:
            page_path = write_page_override(ds, args.page)
            print(f"[OK] Created: {page_path}")
        
        print(f"\n[DIR] Design system saved to: {OUTPUT_DIR}")
        print(f"   MASTER.md (global)")
        if args.page:
            print(f"   pages/{args.page}.md (override)")
    else:
        # Print summary to stdout
        print(f"\n[STYLE] Style: {ds['style']['name']}")
        print(f"[COLOR] Colors: {ds['color_palette']['name']}")
        print(f"[FONT] Typography: {ds['typography']['name']}")
        print(f"[CHARTS] Charts: {', '.join(c['name'] for c in ds['charts'])}")
        print(f"[LANDING] Landing: {ds['landing_pattern']['name']}")

if __name__ == "__main__":
    main()