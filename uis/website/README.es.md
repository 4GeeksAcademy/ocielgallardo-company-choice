# HealthCore Website

Aplicación pública de Next.js para HealthCore.

## Propósito

- Migrar el sitio público desde archivos estáticos a componentes reutilizables.
- Mantener landing y formulario de aplicación en la nueva arquitectura.
- Separar claramente experiencia pública y módulos internos.

## Stack

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS 4

## Estructura

- `app/` rutas y layout
- `components/` secciones reutilizables y formulario
- `lib/` contenido y datos de presentación
- `public/` assets estáticos
- `styles/` reservado para estilos futuros

## Rutas

- `/` landing pública
- `/application` formulario de aplicación con validación en cliente

## Ejecución

```bash
cd uis/website
npm install
npm run dev
```
