# uis

Este directorio contiene las aplicaciones frontend del monorepo.

## Aplicaciones

### website

Aplicación pública de Next.js para la comunicación externa de HealthCore.

- Propósito: landing pública y flujo de formulario de aplicación de paciente.
- Stack: Next.js 16, React 19, TypeScript, Tailwind CSS 4.
- Rutas:
  - `/` landing pública
  - `/application` formulario con validación en cliente

Ejecución:

```bash
cd uis/website
npm install
npm run dev
```

### backoffice

Aplicación interna de Next.js para personal de HealthCore.

- Propósito: espacio operativo interno y base para módulos futuros.
- Incluye el pipeline de candidaturas de People & Talent (migrado desde `uis/talent-pipeline-tracker`).
- Integra utilidades TypeScript de Hito 2 desde `src/` raíz (sin duplicar lógica de negocio).
- Secciones principales:
  - Dashboard
  - Patients
  - Appointments
  - Billing
  - Claims
  - Reports
  - People & Talent (`/applications`, `/candidates/[id]`)

Ejecución:

```bash
cd uis/backoffice
npm install
npm run dev
```

## Límites

- La experiencia pública vive en `website`.
- Los flujos internos viven en `backoffice`.
- La lógica de dominio se reutiliza desde `src/` y paquetes compartidos.
- Evitar duplicación de reglas de negocio entre aplicaciones UI.
