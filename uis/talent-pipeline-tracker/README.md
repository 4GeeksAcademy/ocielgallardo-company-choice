# Talent Pipeline Tracker

Herramienta interna de **People & Talent** para HealthCore Digital. Permite al equipo gestionar el pipeline de candidaturas consumiendo la [Talent Tracker API](https://playground.4geeks.com/tracker/api/v1/docs) del 4Geeks Playground.

## Funcionalidades

- Listado de candidaturas con nombre, puesto, estado y etapa
- Filtros por estado y etapa, y búsqueda por nombre o email (sin recargar la página)
- Vista maestro-detalle: listado + panel de detalle
- Cambio de estado y etapa desde el detalle
- Notas internas (crear y eliminar)
- Registro y edición de candidaturas con validación

## Requisitos

- Node.js 18+
- npm

## Configuración

```bash
cd uis/talent-pipeline-tracker
npm install
cp .env.local.example .env.local
```

Variables de entorno:

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `NEXT_PUBLIC_TRACKER_API_URL` | Base URL de la API | `https://playground.4geeks.com/tracker/api/v1` |

## Desarrollo

```bash
npm run dev
```

Abrir [http://localhost:3000](http://localhost:3000) — redirige a `/applications`. El detalle de cada candidato está en `/candidates/[id]`.

## Producción

```bash
npm run build
npm start
```

## API utilizada

| Método | Endpoint | Uso |
|--------|----------|-----|
| GET | `/records?limit=100` | Cargar candidaturas |
| GET | `/records/{id}` | Detalle en `/candidates/[id]` |
| POST | `/records` | Nueva candidatura |
| PUT | `/records/{id}` | Editar datos |
| PATCH | `/records/{id}` | Cambiar estado/etapa |
| GET | `/records/{id}/notes` | Listar notas |
| POST | `/records/{id}/notes` | Añadir nota |
| DELETE | `/records/{id}/notes/{note_id}` | Eliminar nota |

## Stack

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS 4
