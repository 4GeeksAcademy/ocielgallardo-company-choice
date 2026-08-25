# Informe de auditoría de rendimiento — HealthCore

**Hito:** Auditoría de Rendimiento Frontend (4Geeks Academy)  
**Rama:** `feature/performance-audit` (desde `main`)  
**Estado al 2026-08-25 (noche):** fixes aplicados + baseline documentado; **remeición “after” aún no válida** (ver §3)

---

## 1. Resumen del progreso

| Paso | Estado |
|------|--------|
| Medición inicial (before) | Hecho — `audit/before/` (HTML + PNG) |
| Análisis y causa raíz | Hecho — `AUDIT.md` |
| Correcciones de código | Hecho — commits en esta rama |
| Componente reutilizable | Hecho — `AuthPageShell` |
| Remeición after | **Parcial / inválida** — HTML en `audit/after/`, ver §3 |
| Cierre con deltas medibles | **Pendiente para mañana** |

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

## 4. Primera pasada after (2026-08-25 noche) — **no usar como delta final**

Archivos guardados en `audit/after/`:

| Archivo | URL | Observación |
|---------|-----|-------------|
| `Website-mobile-test.html` | `/` | **`PROTOCOL_TIMEOUT`** — corrida inválida |
| `Backoffice-mobile-test.html` | `/login` | **`PROTOCOL_TIMEOUT`** — corrida inválida |
| `Website-descktop-test.html` | `/` | Completó; aviso IndexedDB (preferir incógnito) |
| `Backoffice-descktop-test.html` | `/login` | Completó |
| `Backoffice-mobile-inside-test.html` | `/` | Completó; aviso de extensiones de Chrome |
| `Backoffice-desktop-inside-test.html` | `/` | Completó |

**Conclusión de esta noche:** la percepción de “siguen iguales” es coherente con (1) timeouts en móvil, (2) medición aún en `next dev` (TBT inflado), (3) posibles extensiones / caché. **No se rellenan deltas oficiales hasta una remeición limpia.**

Tabla after (oficial): **aplazada a mañana**.

| Superficie | Modo | Perf | A11y | BP | SEO | Δ Perf |
|------------|------|-----:|-----:|---:|----:|--------|
| Website `/` | Mobile | — | — | — | — | pendiente |
| Website `/` | Desktop | — | — | — | — | pendiente |
| Backoffice `/login` | Mobile | — | — | — | — | pendiente |
| Backoffice `/login` | Desktop | — | — | — | — | pendiente |
| Backoffice `/` | Mobile | — | — | — | — | pendiente |
| Backoffice `/` | Desktop | — | — | — | — | pendiente |

---

## 5. Qué tuvo (o debería tener) más impacto

| Prioridad | Fix | Por qué |
|-----------|-----|---------|
| 1 | Hero `next/image` + priority | Ataca LCP / bytes del website |
| 2 | `next/dynamic` del playground | Reduce JS crítico del dashboard |
| 3 | `AuthPageShell` + `tabIndex` menú | A11y + mantenibilidad |

---

## 6. Checklist para mañana

1. Reiniciar website (`:3000`) y backoffice (`:3001`) en `feature/performance-audit`.
2. Chrome **Incógnito** (sin extensiones).
3. Repetir las **6** auditorías; descartar cualquier corrida con `PROTOCOL_TIMEOUT`.
4. Sustituir/añadir HTML + PNG en `audit/after/` (nombres claros).
5. Opcional recomendado: `npm run build && npm run start` en cada app y medir en producción local.
6. Actualizar esta tabla §4 con puntuaciones y deltas; cerrar el hito / PR.

---

## 7. Commits relevantes en la rama

- `fa199de` — baseline + fixes de frontend  
- `e33172b` — capturas PNG before + regla `.cursor/rules/read-agents.mdc`  
- (este commit) — HTML after + documentación del checkpoint
