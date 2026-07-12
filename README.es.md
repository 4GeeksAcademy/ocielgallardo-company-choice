# Proyecto de Compañía - Ingeniería de IA — Plantilla para estudiantes

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

_Plantilla base para proyectos transversales del Programa de Carrera en Ingeniería de IA — 4Geeks Academy._

_Las instrucciones están [disponibles en inglés](./README.md)._

---

## Mis Contribuciones

- Desarrollo Frontend
- Arquitectura de Componentes
- Diseño Responsivo
- Desarrollo de formularios y validaciones

---

## Propósito

Este repositorio es la **plantilla de inicio** para los proyectos transversales. Trabajarás con escenarios de empresas reales (Brasaland, TrackFlow, Nexova) construyendo entregables que se corresponden con los hitos del curso (Web, Programación, Backend, Telemetría, RAG, Agentes, Workflows, Tiempo real).

- Crea una plantilla a partir de este repositorio.
- Reemplaza el `CONTEXT.md` placeholder por el contexto de tu empresa asignada.
- Usa `skills/` y los `README.md` por carpeta como guía de trabajo.

---

## Progreso actual de implementación (HealthCore)

Este repositorio ya no es solo una estructura base. Ahora incluye entregables concretos para el escenario de HealthCore, cubriendo el Hito 1 (Web) y partes clave del Hito 2 (Programación).

### 1) Entregables web completados

- Landing page responsive completa en `index.html`.
- Estructura semántica (`header`, `nav`, `main`, `section`, `article`, `footer`).
- Metadatos SEO y sociales (Open Graph, Twitter cards).
- Datos estructurados (JSON-LD) para contexto organizacional/negocio.
- Página de formulario responsive y accesible en `application.html`.
- Lógica de validación frontend en `validation.js`.

### 2) Modelo de dominio y utilidades TypeScript completadas

Implementado en `src/`:

- `src/types/models.ts`
	- Entidades tipadas para el dominio de HealthCore (empresa, departamentos, pacientes, citas, facturas, predicciones, alertas y filtros).

- `src/utils/collections.ts`
	- Utilidades de filtrado:
		- `findOneById`
		- `filterByCategory`
		- `filterByStatus`
		- `filterByProbabilityRange`
		- `filterCritical`
	- Utilidades de ordenamiento:
		- `sortByField` (ascendente/descendente)
		- `sortByMultipleFields` (ordenamiento multicampo)

- `src/utils/search.ts`
	- Utilidades de búsqueda:
		- `linearSearch`
		- `linearSearchUnsorted`
		- `linearSearchByField`
		- `binarySearchByNumber`
		- `binarySearchByField`

- `src/utils/transformations.ts`
	- Utilidades de reportes y agregación:
		- `calculateNoShowRate`
		- `calculateInvoiceRejectionRate`
		- `generateCriticalAlerts`
		- `groupAlertsByStatus`
		- `countByCategory`
		- `calculateTotal`
		- `calculateAverage`
		- `calculateMax`
		- `calculateMin`

- `src/utils/validations.ts`
	- Validaciones de negocio contextuales alineadas a HealthCore (incluyendo baseline de no-show del 22% y rechazo de facturación del 14%).
	- Orquestador de validación previa al procesamiento:
		- `validateRecordBeforeProcessing(...)`

### 3) Comando de validación de tipos disponible

El proyecto incluye un comando claro de validación TypeScript en `packages/shared/package.json`:

```bash
cd /workspaces/ocielgallardo-company-choice/packages/shared
npm run test:types:models
```

Este comando ejecuta verificación estricta de tipos sobre:

- `src/types/models.ts`
- `src/types/models.type-test.ts`

### 4) Playground visual temporal para utilidades

Hay un entorno temporal para validar salidas de utilidades manualmente:

- `test.html`
- `test-playground.js`
- `test-data.js`

Ejecución local:

```bash
npx http-server . -p 3000 -a 0.0.0.0
```

Luego abrir:

`http://localhost:3000/test.html`

---

## Estado actual de la plantilla

Actualmente el repositorio conserva la estructura base, pero además incluye implementación activa del proyecto HealthCore.

- `CONTEXT.md` fue sustituido por el contexto de HealthCore y se usa como base de implementación.
- `AGENTS.md` en raíz ya define comportamiento requerido para agentes IA y reglas de contribución.
- La capa UI quedó separada en dos apps independientes: `uis/website` (pública) y `uis/backoffice` (interna).
- `services/` ahora incluye límites escalables (placeholders) para APIs futuras.
- Existe metadata del paquete compartido en `packages/shared/package.json` (`@repo/shared-types`) con comando funcional de pruebas de tipos TypeScript.

---

## Estructura del repositorio

```text
ai-engineering-company-project-monorepo/
├── README.md
├── README.es.md
├── CONTEXT.md                # Placeholder a reemplazar con el contexto asignado
├── agents/                   # Patrones/plantillas de agentes y documentación de tools
├── data/                     # raw, process, pipelines, eval
├── docs/                     # Documentación de proyecto y arquitectura
├── infra/                    # Docker, Terraform, configuraciones de despliegue
├── internal/                 # CLIs, scripts de migración empaquetados, utilidades internas
├── mcps/                     # Servidores Model Context Protocol (MCP)
├── packages/
│   └── shared/               # Paquete compartido (@repo/shared-types)
├── scripts/                  # Convenciones/documentación de scripts
├── services/                 # APIs y workers en segundo plano
├── shared/                   # Recursos/convenciones compartidas a nivel repo
├── skills/                   # Skills reutilizables para agentes
├── uis/                      # Interfaces de usuario (React, Next.js, Streamlit, HTML)
└── workflows/                # Documentación de automatizaciones/orquestación
```

---

## Cómo empezar

1. **Usa este repositorio como plantilla** y crea tu propio repo de proyecto.
2. **Clona** tu repositorio (o ábrelo en Codespaces).
3. **Reemplaza** `CONTEXT.md` con el contexto completo de tu empresa asignada.
4. **Revisa** los `README.md` de cada carpeta raíz para entender responsabilidades (`uis/`, `services/`, `data/`, `skills/`, etc.).
5. **Empieza a implementar** entregables por hito en `uis/` y `services/`, reutilizando `packages/shared/` y `data/` según corresponda.

---

## Hitos (referencia)

| Hito | Enfoque       | Entregables típicos                              |
| ---- | ------------- | ------------------------------------------------ |
| 0    | Prework       | Configuración del entorno, primeros prompts      |
| 1    | Web           | Sitio corporativo, formularios, SEO              |
| 2    | Programación  | Lógica de negocio, puntuación, cálculos          |
| 3    | UI con IA     | Interfaces generadas con IA                      |
| 4    | Next.js       | Portales, app de fidelización, UI de operaciones |
| 5    | Backend       | API central (ubicaciones, menús, ventas, etc.)   |
| 6    | Telemetría    | Pipeline de datos, dashboards                    |
| 7    | RAG y memoria | Base de conocimiento semántica, búsqueda         |
| 8    | Agentes       | Agentes de soporte, onboarding, formación        |
| 9    | Workflows     | Automatizaciones con n8n                         |
| 10   | Tiempo real   | Dashboards en vivo, alertas, streaming           |

---

## Enlaces

- [4Geeks Academy — Ingeniería de IA](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [Cómo empezar un proyecto de código](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contribuidores

Esta plantilla fue creada como parte del Programa de Carrera de Ingeniería de IA de 4Geeks Academy por [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) y [@alezanchezr](https://x.com/alesanchezr), junto a otros muchos colaboradores. Descubre más sobre nuestro [Curso de Ingeniería de IA](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia) y sobre [otros cursos](https://4geeksacademy.com/es/comparar-programas).

Puedes encontrar otras plantillas y recursos similares en la [página de GitHub de 4Geeks Academy](https://github.com/4geeksacademy).

_Esta plantilla la mantiene 4Geeks Academy para el track de Ingeniería de IA. Uso exclusivo del programa._
