# Mediciones final (post-P7)

**Cuándo:** después de `docker compose up --build` con la rama actual (incluye lazy viewport P7, commit `17b0d6e`+).

**Diferencia vs `audit/after/`:** la pasada del 2026-08-28 midió código **antes** de P7 lazy. Esta carpeta captura el estado **final** del hito.

## Protocolo

1. Chrome **Incógnito** (evitar IndexedDB / extensiones).
2. Stack: `docker compose up --build` (Docker prod, `next start`).
3. Mismas **6 superficies** que `audit/after/`:

| # | URL | Modo Lighthouse | Nombre sugerido del HTML |
|---|-----|-----------------|--------------------------|
| 1 | `http://localhost:3000/` | Mobile | `website-mobil-test.html` |
| 2 | `http://localhost:3000/` | Desktop | `website-desktop-test.html` |
| 3 | `http://localhost:3001/login` | Mobile | `backoffice-mobil-login-test.html` |
| 4 | `http://localhost:3001/login` | Desktop | `backoffice-desktop-login-test.html` |
| 5 | `http://localhost:3001/` (autenticado) | Mobile | `backoffice-mobil-test.html` |
| 6 | `http://localhost:3001/` (autenticado) | Desktop | `backoffice-desktop-test.html` |

## Prioridad de lectura (KPI-first)

Analiza en este orden por corrida; deja A11y/BP/SEO para después:

1. **Performance score**
2. **LCP**
3. **INP** (o maxPotentialFID si INP no aparece en el export)
4. **CLS**
5. **TTFB**
6. **TBT** (lab; complemento de interactividad)

## Post-paso

```bash
node scripts/extract-lighthouse-kpis.mjs audit/final/*.html --markdown
```

Rellenar [`REPORT.md`](../REPORT.md) §4.3 con:

- **Δ vs `audit/before/`** — mejora total del hito
- **Δ vs `audit/after/`** — impacto F5–F7 (sobre todo P7 lazy)

Tabla resumen de referencia: [`AUDIT.md`](../AUDIT.md) §3.
