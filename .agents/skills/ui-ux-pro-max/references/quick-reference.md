# Quick Reference — All UX Guidelines

## Accessibility (CRITICAL)
1. Contrast 4.5:1 minimum for text (AA)
2. Alt text for all images
3. Keyboard navigation for all interactive elements
4. ARIA labels on icon-only buttons
5. Focus visible indicators
6. Page language specified
7. Heading structure (h1-h6)
8. Live regions for dynamic content
9. Form labels programmatically associated
10. Error identification and suggestions

## Touch & Interaction (CRITICAL)
11. Minimum 44×44px touch targets
12. 8px+ spacing between interactive elements
13. Loading feedback for async actions
14. No reliance on hover only
15. No instant state changes (0ms transitions)

## Performance (HIGH)
16. WebP/AVIF images with fallbacks
17. Lazy loading for below-fold content
18. Reserve space to prevent CLS < 0.1
19. No layout thrashing
20. Optimize bundle size

## Style Selection (HIGH)
21. Match style to product type
22. Consistency across all components
23. SVG icons (no emoji)
24. No mixing flat & skeuomorphic randomly

## Layout & Responsive (HIGH)
25. Mobile-first breakpoints
26. Viewport meta tag
27. No horizontal scroll
28. No fixed px container widths
29. Don't disable zoom

## Typography & Color (MEDIUM)
30. Base 16px minimum for body text
31. Line-height 1.5 for body
32. Semantic color tokens (not raw hex)
33. No text < 12px body
34. No gray-on-gray low contrast

## Animation (MEDIUM)
35. Context-aware timing
36. Motion conveys meaning
37. Spatial continuity
38. Not one duration for everything
39. No animating width/height (use transform)
40. Respect prefers-reduced-motion

## Forms & Feedback (MEDIUM)
41. Visible labels (not placeholder-only)
42. Error near field
43. Helper text for complex fields
44. Progressive disclosure
45. No overwhelming upfront

## Navigation Patterns (HIGH)
46. Predictable back behavior
47. Bottom nav ≤ 5 items
48. Deep linking support
49. No overloaded navigation
50. No broken back behavior

## Charts & Data (LOW)
51. Legends on all charts
52. Tooltips on data points
53. Accessible color palettes
54. Not relying on color alone

## Additional Guidelines (55-119)
*See full data/ux-guidelines.csv for complete list with rationale.*