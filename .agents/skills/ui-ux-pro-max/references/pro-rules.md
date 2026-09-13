# Pro Rules — App-Specific Polish & Pre-Delivery Checklist

## Icon Rules
- ✅ Use Lucide Icons (outline, 24×24, stroke-2, round caps)
- ✅ Functional icons: `text-gris-500` default, `text-rojo` active/primary
- ✅ Sizes: `w-4 h-4` (16px), `w-5 h-5` (20px), `w-6 h-6` (24px)
- ❌ No emoji as UI icons
- ❌ No mixing icon libraries in same interface
- ❌ No Font Awesome, Material Icons alongside Lucide

## Touch Feedback
- ✅ Active state: `active:scale-[0.98]` for buttons
- ✅ Hover: `hover:bg-rojo/10` for primary, `hover:bg-gris-100` for secondary
- ✅ Focus: `focus-visible:ring-2 focus-visible:ring-rojo focus-visible:ring-offset-2`
- ✅ Minimum 44×44px touch targets
- ❌ No instant transitions (0ms)

## Dark Mode Contrast
- ✅ Verify all brand colors meet 4.5:1 in both modes
- ✅ Rojo `#C62828` on dark bg: use lighter variant `#EF5350`
- ✅ Grafito `#1F2328` becomes text color in dark
- ✅ Borders: `border-white/10` in dark mode
- ✅ Shadows: reduce opacity in dark mode

## Safe Areas (Mobile)
- ✅ `pt-safe` / `pb-safe` for top/bottom bars
- ✅ `pl-safe` / `pr-safe` for notched devices
- ✅ Bottom navigation: `pb-safe` padding
- ✅ Full-screen modals: account for home indicator

## Pre-Delivery Checklist

### Visual Consistency
- [ ] All colors use semantic tokens (no raw hex in components)
- [ ] Spacing uses 4px base scale consistently
- [ ] Border radius uses defined scale (sm/md/lg/xl/full)
- [ ] Shadows use defined scale (sm/md/lg/xl/glow)
- [ ] Typography follows defined hierarchy
- [ ] Icons use Lucide consistently

### Interaction Quality
- [ ] All buttons have hover, active, focus states
- [ ] Loading states for all async actions
- [ ] Skeleton screens for content loading
- [ ] Empty states with helpful illustrations
- [ ] Error states with clear recovery actions
- [ ] Success confirmations for mutations

### Motion
- [ ] Base duration 150ms used consistently
- [ ] Easing `cubic-bezier(0.4, 0, 0.2, 1)` used
- [ ] `prefers-reduced-motion` respected globally
- [ ] No layout-shifting animations
- [ ] Stagger delays for lists (50ms)

### Accessibility
- [ ] Focus order matches visual order
- [ ] Skip link present and functional
- [ ] ARIA live regions for toasts/notifications
- [ ] Form errors announced and focused
- [ ] Color not sole indicator of state
- [ ] 200% zoom usable
- [ ] High contrast mode tested

### Responsive
- [ ] Mobile (<640px): stacked, full-width
- [ ] Tablet (640-1024px): 2-col grids, collapsible sidebar
- [ ] Desktop (1024-1280px): full layout
- [ ] Wide (>1280px): max-width containers
- [ ] No horizontal overflow at any breakpoint

### Performance
- [ ] Images optimized (WebP/AVIF)
- [ ] Lazy loading below fold
- [ ] Code splitting by route
- [ ] No unnecessary re-renders (React.memo, useMemo)
- [ ] Virtualized long lists
- [ ] CLS < 0.1

### Brand Compliance
- [ ] Rojo `#C62828` used as accent only (5-10%)
- [ ] Grafito `#1F2328` for structure/text (20-30%)
- [ ] Blanco/grises for space (60-70%)
- [ ] Manrope for all UI text
- [ ] JetBrains Mono for code only
- [ ] Gallo microinteractions: loading, 400 error
- [ ] No competing brand colors

### Code Quality
- [ ] TypeScript strict mode
- [ ] No `any` types
- [ ] Components follow shadcn patterns
- [ ] Proper `forwardRef` for UI components
- [ ] `className` merging with `cn()` utility
- [ ] `data-testid` for testing