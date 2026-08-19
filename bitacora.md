# Bitacora del estudiante

## Hito 1

## Sesion 2026-05-22

### Objetivo acordado

Crear una landing page para HealthCore en `index.html` con HTML semantico bien estructurado, enfoque SEO/GEO, usando estilos de Tailwind. En esta etapa no se desarrolla el formulario, solo la landing.

### Alcance realizado

- Se implemento una landing completa en `index.html`.
- Se incluyo estructura semantica: `header`, `nav`, `main`, `section`, `article`, `aside`, `footer`.
- Se agregaron metadatos SEO: `title`, `description`, `keywords`, `canonical`, `robots`.
- Se agregaron metadatos sociales: Open Graph y Twitter Cards.
- Se agrego JSON-LD para `Organization` y `FAQPage` (GEO/SEO tecnico).
- Se incorporaron secciones de contenido: Hero, indicadores, servicios, vision/mision/valores, testimonios y FAQ.
- Se conecto CTA hacia `application.html` para la futura etapa de formulario.

### Fuente de contenido usada

Se obtuvo contenido publico de referencia de <https://www.health-core.org/> via lectura en texto para construir copy base (servicios, vision, mision, valores y enfoque regional).

### Pendientes para siguiente actualizacion

- Ajustar el copy final de marca con validacion del cliente.
- Integrar assets oficiales finales (logo definitivo, paleta exacta, imagenes de marca).
- Implementar y conectar formulario definitivo en `application.html` + validaciones avanzadas.
- Revisar performance y accesibilidad (Lighthouse y contraste).

## Actualizacion 2026-05-22 (iteracion responsive + logo)

### Solicitud del cliente

Incluir un logo similar a un globo terraqueo y asegurar comportamiento responsive para movil.

### Cambios aplicados

- Se agrego un logo vectorial SVG tipo globo en la marca principal del header.
- Se mejoro la navegacion en movil con accesos visibles debajo del nav principal.
- Se optimizo el Hero para pantallas pequeñas:
  - tipografia escalable en `h1` y parrafo.
  - botones CTA apilados en movil y en fila en pantallas medianas/grandes.
  - ajustes de espaciado vertical para mejor lectura.

### Resultado

La landing mantiene consistencia visual en desktop y mejora usabilidad en movil sin perder enfoque SEO/GEO.

## Actualizacion 2026-05-22 (Schema Organization)

### Solicitud del cliente

Añadir marcado Schema.org tipo `Organization` para la empresa.

### Cambios aplicados

- Se reforzo el bloque JSON-LD `Organization` ya presente en `index.html`.
- Se añadieron propiedades recomendadas: `@id`, `logo`, `image`, `foundingLocation` y `contactPoint`.

### Resultado

El marcado estructurado de organizacion queda mas completo y util para buscadores tradicionales y motores generativos.

## Actualizacion 2026-05-23 (sitio completo HealthCore)

### Solicitud del cliente

Crear sitio web profesional, responsive y accesible para HealthCore con stack HTML5 semantico + Tailwind CDN + JavaScript Vanilla, incluyendo landing y formulario con validaciones completas.

### Cambios aplicados

- Se reconstruyo `index.html` completo con enfoque mobile-first y estructura semantica: `header`, `nav`, `main`, `section`, `article`, `footer`.
- Se implemento header sticky con navegacion desktop y menu movil accesible (toggle con JS vanilla).
- Se agregaron secciones solicitadas: Hero, Servicios, Beneficios, Experiencia del Paciente y CTA final.
- Se incluyeron metadatos SEO: `title`, `meta description`, `keywords`, Open Graph y Twitter cards.
- Se implemento JSON-LD tipo `MedicalBusiness` con nombre, telefono, direccion, area de servicio y sitio web.
- Se reconstruyo `application.html` con formulario semantico profesional usando `fieldset`, `legend`, labels y campos requeridos.
- Se agregaron campos personales y medicos completos, consentimiento obligatorio y botones de envio + reset.
- Se reescribio `validation.js` con validacion en tiempo real, blur y submit, mensajes especificos por campo y estado visual de error/exito.

### Resultado

Sitio funcional listo para ejecutar localmente, con experiencia responsive en movil/tablet/desktop y base solida de accesibilidad, SEO y validacion de formulario.

## Hito 2

## Actualizacion 2026-06-12 (TypeScript: modelos y filtros iniciales)

### Solicitud del cliente

Leer los archivos de contexto y comenzar implementacion en TypeScript basada en `company-choice.md`, creando interfaces de entidades y funciones de filtrado en la estructura `src/` definida.

### Rama de trabajo

- Se creo la rama: `feature/healthcore-ts-models-filters`.

### Cambios aplicados

- Se creo `src/types/models.ts` con interfaces y tipos para las entidades del caso HealthCore:
  - Empresa, DepartamentoInteres, RetoProyecto, Paciente, Cita, Factura.
  - PrediccionNoShow, PrediccionRechazoFactura, AlertaCritica.
  - Tipos de apoyo para categoria, estado y filtros criticos.
- Se creo `src/utils/collections.ts` con funciones de filtrado para busqueda individual y filtros combinados:
  - `buscarUnoPorId`.
  - `filtrarPorCategoria`, `filtrarPorEstado`, `filtrarPorRangoProbabilidad`.
  - `filtrarCriticos` (multiples criterios en una sola consulta).
- Se creo `src/utils/search.ts` con algoritmos de busqueda:
  - Busqueda lineal generica y por campo.
  - Busqueda binaria por valor numerico en colecciones ordenadas.
- Se creo `src/utils/transformations.ts` con agregaciones para reportes:
  - Tasa de no-show.
  - Tasa de rechazo de facturas.
  - Generacion de alertas criticas y agrupacion por estado.
- Se creo `src/utils/validations.ts` con validaciones de negocio base:
  - Validacion de probabilidades en rango 0-1.
  - Validaciones para citas, facturas y predicciones criticas.

### Resultado

Queda lista la base TypeScript de entidades y utilidades para continuar con siguientes iteraciones (datos de prueba, integracion UI/API, tests y reglas avanzadas).

Queda lista la base TypeScript de entidades y utilidades para continuar con siguientes iteraciones (datos de prueba, integracion UI/API, tests y reglas avanzadas).

## Actualizacion 2026-06-13 (ordenamientos y busquedas)

### Solicitud del cliente

Implementar funciones de ordenamiento (ascendente, descendente y multicampo), validar busqueda lineal para arrays desordenados y busqueda binaria para arrays previamente ordenados. Mantener codigo en ingles y comentarios en español.

### Cambios aplicados

- Se actualizo `src/utils/collections.ts` con utilidades de ordenamiento:
  - `sortByField` para ordenar por un campo en `asc` o `desc`.
  - `sortByMultipleFields` para ordenar por multiples campos en cascada.
  - Tipos auxiliares `SortDirection` y `SortRule<T>`.
  - Comparador interno reutilizable para numeros, booleanos y texto.
- Se actualizo `src/utils/search.ts` para cubrir explicitamente los escenarios de busqueda:
  - `linearSearchUnsorted` para arrays desordenados.
  - `binarySearchByField` para arrays ya ordenados por un campo.
  - Se conservaron `linearSearch`, `linearSearchByField` y `binarySearchByNumber`.

### Resultado

El proyecto ya cuenta con filtros, ordenamientos y busquedas esenciales para trabajar colecciones en diferentes criterios con una base simple y reutilizable.

## Actualizacion 2026-06-13 (validaciones de negocio contextuales)

### Solicitud del cliente

Implementar validaciones de negocio antes de procesar datos, alineadas a `CONTEXT.md` y `company-choice.md`, con funciones de responsabilidad unica, tipos explicitos y reglas fieles al contexto.

### Cambios aplicados

- Se reforzo `src/utils/validations.ts` con reglas de negocio especificas de HealthCore:
  - Benchmarks contextuales: no-show `22%` y rechazo de facturacion `14%`.
  - Alcance geografico permitido: `US` y `United Kingdom`.
  - Validaciones por entidad: `Company`, `ProjectChallenge`, `FocusDepartment`, `Patient`, `Appointment`, `Invoice`, `NoShowPrediction`, `InvoiceRejectionPrediction`.
  - Validaciones de consistencia por contexto:
    - `Appointment.category` debe ser `Patient Experience and Access`.
    - `Invoice.category` debe ser `Revenue Cycle and Billing`.
    - Moneda por pais del paciente (`US -> USD`, `United Kingdom -> GBP`) cuando se dispone del pais.
    - Umbral critico de predicciones no inferior a baseline contextual (`0.22` no-show, `0.14` rechazo).
- Se agrego funcion orquestadora `validateRecordBeforeProcessing(...)` para ejecutar validaciones previas de forma centralizada.
- Se mantuvo el principio de responsabilidad unica con funciones auxiliares pequenas (texto requerido, rangos, valor exacto, alcance de pais y consistencia moneda-pais).

### Resultado

La capa de validaciones ahora es contextual (no generica), tipada explicitamente y lista para usarse como puerta de control antes de procesar objetos del dominio.

## Actualizacion 2026-06-15 (playground visual temporal para pruebas TS)

### Solicitud del cliente

Crear una interfaz temporal e independiente para validar manualmente las utilidades TypeScript ya implementadas, sin tocar `index.html` ni modificar la logica de negocio existente.

### Cambios aplicados

- Se creo `test.html` como pagina aislada de pruebas manuales con Tailwind por CDN.
- Se creo `test-playground.js` para orquestar ejecucion visual de modulos:
  - `Collections`: filtros, ordenamientos y busqueda por id.
  - `Search`: busqueda lineal, lineal en desordenados y binaria.
  - `Transformations`: tasas, alertas, agrupaciones y metricas numericas.
  - `Validations`: validaciones por entidad y validacion integral previa al procesamiento.
- Se creo `test-data.js` con datasets de ejemplo desacoplados (patients, appointments, invoices, predictions), sin mezclar mocks con la logica principal.
- El playground carga y transpila en runtime los archivos TS existentes (`src/utils/*.ts`) para ejecutar las funciones reales sin alterar su implementacion.

### Resultado

Quedo disponible una consola visual temporal para demostracion y pruebas manuales de utilidades TypeScript, ejecutable en local/Codespaces con:

```bash
npx http-server . -p 3000 -a 0.0.0.0
```

## Calidad de Codigo

### Verificacion solicitada

1. Revisar si cada funcion es pura (sin modificar estado global y trabajando con parametros).
2. Revisar manejo de casos vacios y no encontrados (arrays vacios, elementos no encontrados, valores nulos).

### Resultado de pureza

- En general, las funciones de `src/utils/collections.ts`, `src/utils/search.ts`, `src/utils/transformations.ts` y `src/utils/validations.ts` no modifican estado global ni mutan entradas.
- Las funciones de ordenamiento usan copia defensiva (`[...items]`) antes de ordenar.
- Hallazgo puntual: `generateCriticalAlerts(...)` no es estrictamente pura en sentido funcional porque usa `new Date().toISOString()` internamente (depende del tiempo del sistema), aunque no muta estado global.

### Resultado de casos vacios/no encontrados

- Correcto:
  - Busquedas lineales y binarias retornan `undefined` cuando no encuentran elementos o cuando el array esta vacio.
  - Tasas y promedio retornan `0` con arrays vacios.
  - Maximo y minimo retornan `undefined` con arrays vacios.
  - Conteo por categoria retorna objeto vacio `{}` cuando no hay elementos.

### Resultado de valores nulos

- Parcialmente cubierto:
    En `collections.ts`, `compareValues(...)` contempla `null` y `undefined`.
    En validaciones, `phone` y `email` opcionales se manejan de forma segura.
- Riesgo residual:
    Si en runtime llegan `null` en campos que TypeScript tipa como `string`/`array` obligatorios (por ejemplo `invoice.billingCodes` o     `patient.fullName`), algunas validaciones podrian fallar por acceso directo (`.trim()`, `.length`) antes de construir errores de negocio.

### Conclusión

- La base cumple bien para desarrollo tipado en TypeScript y escenarios esperados.
- Existe una mejora pendiente para robustez defensiva ante payloads nulos en runtime no tipados.

## Hito 3

## Actualizacion 2026-06-25 (Talent Pipeline Tracker — People & Talent)

### Objetivo acordado

Construir el frontend que el equipo de **People & Talent** de HealthCore empezará a usar para gestionar el pipeline de candidaturas. La API REST ya estaba expuesta por Tecnología; el entregable es la interfaz en `uis/talent-pipeline-tracker/`.

### Contexto del brief

El departamento recibió más de 100 candidaturas en menos de dos semanas y llevaba el seguimiento en hojas de cálculo, documentos sueltos y correos. La herramienta debía permitir:

- Ver todas las candidaturas de un vistazo (nombre, puesto, estado, etapa).
- Filtrar por estado y etapa, y buscar por nombre o email sin recargar la página.
- Abrir el detalle sin perder el contexto del listado.
- Cambiar estado o etapa desde el detalle con una sola interacción.
- Añadir y eliminar notas internas.
- Registrar candidaturas nuevas y editar datos existentes.

### API utilizada

**Talent Tracker API** del 4Geeks Playground:

- Documentación: <https://playground.4geeks.com/tracker/api/v1/docs>
- Base URL: `https://playground.4geeks.com/tracker/api/v1`
- Recurso principal: `/records` (sin namespace; distinto al patrón inicial de `/applications/{namespace}` del plan)

| Operación | Endpoint | Uso en UI |
| ----------- | ---------- | ----------- |
| Listar | `GET /records?limit=100` | Carga del listado |
| Detalle | `GET /records/{id}` | Panel de candidato |
| Crear | `POST /records` | Nueva candidatura |
| Editar datos | `PUT /records/{id}` | Corrección de datos |
| Cambiar pipeline | `PATCH /records/{id}` | Estado y etapa |
| Notas | `GET/POST/DELETE /records/{id}/notes` | Notas internas |

**Estados:** `received`, `in_progress`, `selected`, `discarded`  
**Etapas:** `pending`, `review`, `personal_interview`, `technical_interview`, `offer_presented`

### Alcance realizado

#### 1) Fundamentos

- Tipos en `lib/types/application.ts` y constantes en `lib/constants/pipeline.ts`.
- Cliente API en `lib/api/client.ts`, `records.ts` y `notes.ts`.
- Layout HealthCore con fuente Inter, metadata y redirect `/` → `/applications`.
- `.env.local.example` con `NEXT_PUBLIC_TRACKER_API_URL`.

#### 2) Listado y filtros

- `ApplicationList`, `ApplicationListItem`, `StatusStageBadge`.
- Filtros por estado y etapa + búsqueda por nombre/email con debounce (300 ms).
- Filtrado en cliente sobre ~100 registros (`lib/utils/filterApplications.ts`).
- Sincronización de filtros y selección con URL (`?status=&stage=&q=&selected=`).

#### 3) Vista maestro-detalle

- Desktop: listado (~40 %) + panel de detalle (~60 %).
- Móvil: listado completo; al seleccionar, panel de detalle con botón «Volver al listado».
- Componente orquestador: `components/ApplicationsWorkspace.tsx`.

#### 4) Mutaciones de pipeline

- `StatusStageControls` en el detalle con `PATCH` y actualización optimista + rollback en error.

#### 5) Notas internas

- `NotesSection` y `NoteForm`: listar, crear y eliminar con confirmación.

#### 6) Formularios

- `ApplicationForm` para crear y editar con validación accesible (`aria-live="polite"`).
- Campos: nombre, email, teléfono, puesto, años de experiencia, LinkedIn opcional.

#### 7) Pulido y documentación

- Estados de carga (skeleton), error (banner con reintento) y vacío (CTA).
- `uis/talent-pipeline-tracker/README.md` y actualización de `uis/README.es.md`.

### Stack

- Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4.

### Criterios de aceptación

- [x] Listado con nombre, puesto, estado y etapa.
- [x] Filtros y búsqueda sin recargar la página.
- [x] Detalle sin perder contexto del listado.
- [x] Cambio de estado/etapa desde el detalle.
- [x] Notas internas (crear y eliminar).
- [x] Registrar y editar candidaturas.
- [x] UI alineada con HealthCore y responsive.

### Verificación técnica

- TypeScript (`tsc --noEmit`): OK.
- ESLint: OK.
- `npm run build`: en Windows puede fallar por longitud de ruta del proyecto (limitación del sistema de archivos), no por errores de código.

### Cómo ejecutar

```bash
cd uis/talent-pipeline-tracker
npm install
npm run dev
```termial
Abrir <http://localhost:3000> → `/applications`.

### Fuera de alcance (MVP)

- Autenticación de usuarios People.
- Drag-and-drop entre etapas.
- Exportar CSV, KPIs de contratación, integración con email.
- Tests automatizados.

### Pendientes opcionales

- Paginación server-side si el volumen supera de forma estable las 100 candidaturas.
- Resolver build en rutas Windows muy largas (mover repo a ruta más corta o habilitar rutas largas en SO).

## Hito 4

## Actualizacion 2026-07-12 (contexto de agentes IA y gobierno documental)

### Solicitud del cliente

Crear el contexto de trabajo para agentes IA del repositorio con alcance **solo documentacion**, sin cambios de logica de negocio, sin refactors y sin modificar configuracion del proyecto.

### Restricciones aplicadas

- No se modifico codigo fuente de `src/`, `uis/`, `services/` ni otros modulos de implementacion.
- No se instalaron dependencias.
- No se realizaron cambios de arquitectura tecnica de la aplicacion.
- Se uso `CONTEXT.md` como fuente de verdad del dominio.
- Se definio como restriccion explicita ignorar `company-choise.md` hasta autorizacion del developer.

### Cambios aplicados

- Se creo/actualizo el Memory Bank para onboarding de agentes:
  - `memory-bank/projectbrief.md`
  - `memory-bank/techContext.md`
  - `memory-bank/progress.md`
- Se creo `AGENTS.md` en la raiz con politicas de comportamiento para agentes:
  - mision del proyecto
  - orden obligatorio de lectura
  - workflow previo a codificar
  - reglas de modificacion de archivos
  - validaciones minimas
  - expectativas de commit y pull request
  - reglas de seguridad y criterios para pedir aclaracion
- Se poblo `.agents/rules/` con reglas enfocadas (una responsabilidad por archivo):
  - `repository-structure.md`
  - `coding-standards.md`
  - `documentation.md`
  - `git-workflow.md`
  - `file-modification-policy.md`
  - `naming-conventions.md`
  - `typescript-guidelines.md`

### Incidencia y resolucion

- Existia una carpeta vacia llamada `AGENTS.md` en la raiz, lo que bloqueaba la creacion del archivo `AGENTS.md`.
- Con confirmacion explicita del usuario, se elimino la carpeta vacia y se creo correctamente el archivo requerido.

### Resultado

El repositorio queda preparado con contexto persistente para nuevos agentes IA, politicas de contribucion claras y reglas operativas en formato markdown, manteniendo intacta la implementacion funcional existente.

## Actualizacion 2026-07-12 (migracion arquitectonica a monorepo escalable)

### Solicitud del cliente

Reestructurar el proyecto a una arquitectura monorepo escalable, separando sitio publico, backoffice interno y base de servicios futuros, preservando funcionalidad existente y reutilizando logica de negocio de Hito 2 sin duplicacion.

### Cambios aplicados

- Se migro la aplicacion interna existente desde `uis/talent-pipeline-tracker/` hacia `uis/backoffice/` para mantener continuidad funcional.
- Se creo una segunda app independiente en `uis/website/` con Next.js App Router y componentes reutilizables para la landing publica y formulario en `/application`.
- Se implemento layout interno propio para backoffice con navegacion base y secciones iniciales:
  - Dashboard
  - Patients
  - Appointments
  - Billing
  - Claims
  - Reports
- Se integro Hito 2 en backoffice mediante imports directos a utilidades de `src/`:
  - `collections.ts`
  - `search.ts`
  - `transformations.ts`
  - `validations.ts`
  - `models.ts`
- Se creo estructura escalable en `services/` sin implementar APIs:
  - `_template-service/`
  - `gateway/`
  - `clinical-operations/`
  - `revenue-cycle/`
  - `compliance/`
- Se actualizaron documentos afectados (`README.md`, `README.es.md`, `uis/README.*`, `services/README.*`, `memory-bank/*`).

### Validacion ejecutada

- `uis/website`:
  - `npm run build` OK
  - `npm run dev -- --port 3100` OK
- `uis/backoffice`:
  - `npm run build` OK
  - `npm run dev -- --port 3101` OK
- Verificacion adicional:
  - imports externos a utilidades de Hito 2 funcionando en dashboard de backoffice
  - sin errores de TypeScript/diagnosticos en apps migradas

### Resultado

La arquitectura queda segmentada por responsabilidad (`website` publico, `backoffice` interno, `services` para APIs futuras), manteniendo la funcionalidad previa y dejando puntos de extension claros para los siguientes hitos.

## Actualizacion 2026-07-31 (utilidad de analisis de incidentes — Pasos 1 y 2)

### Solicitud del cliente

Avanzar el proyecto de analisis de reportes de incidentes de HealthCore (CONTEXT en `docs/data-contract/`) sin escribir logica de negocio todavia: primero diseño funcional del flujo de `analyze.py` (Paso 1), luego estructura de codigo reutilizable para CLI y futura API (Paso 2), y documentar los README de las carpetas tocadas.

### Fuente de verdad usada

- `docs/data-contract/CONTEXT-HealthCore.md` / `CONTEXT-HealthCore.es.md`
- Orden de lectura de `AGENTS.md` (`memory-bank/techContext.md`, `memory-bank/progress.md`, `CONTEXT.md`)

### Paso 1 — Diseño funcional

- Se documento el flujo completo de ejecucion de `analyze.py` (lectura → validacion → metricas → consola → prompt de exportacion).
- Entregables:
  - `docs/data-contract/functional-design-analyze.md`
  - `docs/data-contract/functional-design-analyze.es.md`
- Se dejaron explicitas ambiguedades del CONTEXT (p. ej. 1000 vs 100 filas, reglas no listadas para `incident_id`/`date`, multi-regla por registro).
- Sin codigo y sin estructura de carpetas en este paso.

### Paso 2 — Estructura de codigo (sin implementacion)

- Objetivo: separar orquestacion CLI de logica reutilizable para que la futura API reutilice los mismos modulos.
- Estructura acordada tras revision contra README existentes del monorepo:

```text
scripts/
  └── analyze.py                          # solo coordina el flujo
services/
  └── incidents-analysis/
        ├── __init__.py
        ├── models.py                     # dataclasses compartidos
        ├── csv_reader.py
        ├── validator.py
        ├── analyzer.py
        ├── exporter.py
        └── README.md
data/raw/
  └── incidents-healthcore.csv            # dataset de prueba (PHI)
docs/data-contract/                       # CONTEXT + diseño funcional
```

- Decision de modelo: `dataclass` desde el inicio (preparacion hacia FastAPI/Pydantic).
- Correcciones de ubicacion aplicadas:
  - no dejar modulos `.py` sueltos en la raiz de `services/`
  - un solo paquete de dominio: `services/incidents-analysis/` (fiel al path del CONTEXT)
  - CSV en `data/raw/` (no en raiz de `data/` ni en `pipelines/`)
  - nombre importable `csv_reader.py` (no `csv-reader.py`)

### Documentacion de carpetas actualizada

- `data/raw/README.md` + `README.es.md` — dataset actual, privacidad HIPAA/UK GDPR
- `scripts/README.md` + `README.es.md` — rol de `analyze.py` como entrypoint fino
- `services/incidents-analysis/README.md` — mapa de modulos, reuso CLI/API, compliance, estado Paso 2

### Estado al cerrar Paso 2

- Diseño funcional y estructura de carpetas listos.
- Modulos del servicio son placeholders (sin logica implementada).
- Siguiente paso previsto: implementar el primer modulo (`csv_reader.py`).

```text
Este paso se resolvio en el Paso 3
```

### Resultado

Queda definida la arquitectura minima del analizador de incidentes alineada al monorepo y al CONTEXT, con documentacion de flujo y de responsabilidades por archivo, lista para empezar la implementacion modulo a modulo.

## Actualizacion 2026-07-31 (Paso 3 — inicio de implementacion: models + csv_reader)

### Solicitud del cliente

Empezar la programacion del analizador de incidentes en orden de dependencias (`models` → `csv_reader` → …), implementando el estudiante con guia, sin precipitar modelos de resumen hasta que hagan falta.

### Orden de implementacion acordado

1. `models.py`
2. `csv_reader.py`
3. `validator.py` (pendiente)
4. `analyzer.py` (pendiente)
5. `exporter.py` (pendiente)
6. `scripts/analyze.py` (pendiente)

### Cambios aplicados

- Se renombro el paquete de `services/incidents-analysis/` a `services/incidents_analysis/` para que sea importable en Python (`from services.incidents_analysis...`).
- Se implemento `models.py` con dataclass `Incident` (9 campos del CONTEXT; `satisfaction_score` como `int | None`; comentario PHI en `patient_id`).
- Se implemento `csv_reader.py`:
  - `read_incidents(path) -> list[Incident]`
  - UTF-8 + `csv.DictReader`
  - celda vacia de score → `None`
  - sin reglas de negocio ni impresion de `patient_id`
- Validacion local del lector: `len(read_incidents(...)) == 100` con el CSV oficial.
- Se incorporo el dataset real `data/raw/incidents-healthcore.csv` desde el syllabus de 4Geeks:
  - Origen: `https://github.com/4GeeksAcademy/ai-engineering-syllabus` → `content/contexts/incidents-file-analysis/incidents-healthcore.csv`
  - Antes solo existia un placeholder vacio en el monorepo.
- Se actualizo `.gitignore` para ignorar artefacto Python:
  - `__pycache__/`
  - `*.py[cod]`
  - `*$py.class`
- Nota operativa: si `__pycache__` ya estaba en staging, sacarlo con `git rm -r --cached` (no versionar bytecode).

### Decisiones de diseño reforzadas

- La proteccion de `patient_id` (no imprimir / log / exportar) **no** se implementa en `models.py`; se aplica en validator, consola y exporter.
- `models.py` solo define la forma del registro; no valida ni lee archivos.

### Estado

- Completados: `models.py`, `csv_reader.py`, CSV de prueba, paquete importable.
- Siguiente modulo: `validator.py` (7 reglas del CONTEXT + conteos por regla sin exponer PHI).

### Resultado

Queda operativa la base de datos tipada y la lectura del CSV oficial de HealthCore; el flujo de implementacion puede continuar con la capa de validacion.

## Actualizacion 2026-07-31 (Paso 3 — cierre del pipeline CLI)

### Solicitud del cliente

Completar la implementacion del analizador de incidentes (validator → analyzer → exporter → `analyze.py`), documentar carpetas afectadas y dejar el script listo frente al CONTEXT.

### Modulos implementados y validados

- `validator.py`: 7 reglas del CONTEXT; primera falla por registro; sin exponer `patient_id`.
  - Prueba: `100` total → `94` validos → `6` invalidos (1 por regla principal del breakdown).
- `analyzer.py`: totales, categoria, estado, pais (recomendado), satisfaccion (`average` 3.58, histograma 1–5).
  - Usa `collections.Counter` (stdlib de Python).
- `exporter.py`: CSV de metricas `metric` / `value` / `percentage` en modo `"w"` (resumen de una corrida, no append).
  - Salida por defecto: `data/process/results.csv`.
- `scripts/analyze.py`: orquesta reader → validator → analyzer → consola → prompt `Export results to CSV? [y / n]`.
  - Anade la raiz del repo a `sys.path` para importar `services.incidents_analysis`.

### Validacion ejecutada

```bash
python scripts/analyze.py data/raw/incidents-healthcore.csv
```

- Informe de consola alineado a numeros del CONTEXT (totales, invalidos, categorias, estados, satisfaccion; pais incluido).
- Exportacion regenera `data/process/results.csv` al responder `y`.

### Documentacion actualizada en este cierre

- `bitacora.md` (esta entrada).
- `data/process/README.md` + `README.es.md` — artefacto `results.csv`.
- `services/incidents_analysis/README.md` — estado implementado (ya no placeholders).
- `scripts/README.md` + `README.es.md` — ruta correcta `incidents_analysis`.
- `services/README.md` + `README.es.md` — se lista el servicio de analisis de incidentes.
- `.gitignore` — se ignora `data/process/results.csv` (salida regenerable).

### Estado

- **Cerrado:** pipeline CLI completo del CONTEXT (script + servicios reutilizables).
- **Siguiente hito del proyecto (fuera de este cierre):** API FastAPI + UI que reutilice los mismos modulos (`POST /api/incidents/analyze` o equivalente).

### Resultado

El estudiante puede analizar el CSV oficial de HealthCore de extremo a extremo con logica separada del entrypoint, lista para reutilizar en una API futura.

## Actualizacion 2026-08-01 (Fase 2 — API FastAPI + UI backoffice)

### Solicitud del cliente

Integrar la logica reutilizable de `services/incidents_analysis/` en la plataforma:

- Backend: `POST /api/incidents/analyze` (CSV multipart) y `GET /api/incidents/results/export` (CSV del ultimo analisis).
- Frontend: pagina de analisis de incidencias en `uis/backoffice`, accesible desde el menu, con upload, resumen en pantalla y descarga CSV.
- Nombres de categorias, estados y reglas invalidas alineados al CONTEXT HealthCore (sin exponer `patient_id`).

### Backend implementado

- `services/app/main.py` — app FastAPI, CORS para `localhost:3000` / `127.0.0.1:3000`, registro del router.
- `services/app/routers/incidents.py` — endpoints HTTP; el router solo orquesta, la logica de negocio sigue en `incidents_analysis/` (vía `domain/incident_service.py`).
  - `POST /api/incidents/analyze`: acepta `multipart/form-data` campo `file`; valida extension `.csv`; ejecuta `read_incidents` → `validate_incidents` → `analyze_incidents`; persiste ultimo resumen con `export_results` en `data/process/results.csv`; responde JSON.
  - `GET /api/incidents/results/export`: sirve el ultimo CSV (`FileResponse`); `404` si no hay analisis previo.

### Frontend implementado (`uis/backoffice`)

- Menu: entrada **Incidents** → `/incidents` en `BackofficeShell.tsx`.
- Pagina: `app/incidents/page.tsx` (upload → analizar → resumen → descargar).
- Componentes:
  - `IncidentCsvUpload.tsx` — selector + drag & drop (solo `.csv`).
  - `IncidentAnalysisSummary.tsx` — totales, `invalid_breakdown` por regla CONTEXT, `by_category`, `by_status`, indice de satisfaccion.
- Cliente: `lib/services/healthcoreApi.ts` → `NEXT_PUBLIC_HEALTHCORE_API_URL` (default `http://127.0.0.1:8000`). El cliente Tracker (`client.ts`) no se modifico.
- Tipos: `types/incidents.ts` con claves CONTEXT (`APPOINTMENT`, `OPEN`/`CLOSED`/`DISCARDED`, reglas `invalid_*`, etc.).

### Como arrancar (validacion local)

```bash
# API (raiz del repo)
python -m uvicorn services.app.main:app --reload

# UI
cd uis/backoffice
npm run dev
```

- Abrir `/incidents`, subir `data/raw/incidents-healthcore.csv`.
- Esperado: ~100 total / 94 validos / 6 invalidos; desglose de invalidos por regla; descarga de `results.csv`.

### Estado

- **Cerrado:** Fase 2 integracion API + UI sobre la misma pipeline del CLI.
- La logica de negocio permanece en un solo lugar: `services/incidents_analysis/`.

### Resultado

Priya Nair (Patient Access) puede analizar el CSV de incidentes desde el backoffice HealthCore y exportar metricas sin PHI, reutilizando exactamente el cerebro del script CLI.

## Hitos alcanzados

- ✅ Arquitectura del analizador definida.
- ✅ Separación entre CLI y lógica de negocio.
- ✅ Modelo `Incident` implementado mediante `dataclass`.
- ✅ Lectura del CSV oficial de HealthCore.
- ✅ Validación completa según el CONTEXT.
- ✅ Cálculo de métricas y generación del resumen.
- ✅ Exportación de resultados a CSV.
- ✅ Pipeline CLI funcional y preparado para reutilizarse en FastAPI.
- ✅ API FastAPI: `POST /api/incidents/analyze` + `GET /api/incidents/results/export`.
- ✅ UI backoffice `/incidents` (upload, resumen CONTEXT, descarga CSV).

## Próximo objetivo

Endurecer validacion HTTP de errores de entrada (fichero vacio / CSV ilegible) si el evaluador lo exige de forma explicita; documentar dependencias Python (`fastapi`, `uvicorn`, `python-multipart`) en un `requirements` del servicio API si se estandariza el empaquetado.

## Actualizacion 2026-08-04 (alineacion documental Milestone 09)

### Solicitud del cliente

Registrar en bitacora los cambios recientes de `docs/` como evidencia de alineacion con el proyecto academico.

### Cambios documentados

- Se incorporo una nueva seccion de contexto para el hito **09 - Lightweight Storage API** en `docs/supplier-directory/`.
- Se agregaron los archivos:
  - `docs/supplier-directory/CONTEXT-HealthCore.md` (ingles).
  - `docs/supplier-directory/CONTEXT-HealthCore.es.md` (espanol).
- La nueva documentacion define el dominio **Supplier Directory** de HealthCore:
  - modelo de proveedor;
  - categorias y estados validos;
  - dataset semilla (`SUPPLIERS_SEED`);
  - restricciones de negocio (moneda por pais, trazabilidad de tarifa, suspension en lugar de borrado);
  - requerimientos funcionales para frontend.

### Resultado

La base documental del repositorio queda actualizada para iniciar implementacion de almacenamiento ligero (TinyDB) en las rutas permitidas por la academia, con reglas de negocio y alcance funcional claramente definidos.

## Actualizacion 2026-08-04 (orden de runtime en data + ignore de artefactos)

### Solicitud del cliente

Ordenar los archivos entregados por la API dentro de `data/` por responsabilidad, sin eliminar contenido, y evitar versionar archivos runtime locales.

### Cambios aplicados

- Se movio `data/suppliers.json` a `data/process/suppliers/suppliers.json` para alinear persistencia TinyDB con la carpeta de outputs operativos.
- Se actualizo `services/app/core/database.py` para leer/escribir TinyDB desde la nueva ruta:
  - `data/process/suppliers/suppliers.json`
- Se actualizo `.gitignore` para no versionar artefactos runtime:
  - `data/process/results.csv`
  - `data/process/suppliers/suppliers.json`

### Validacion ejecutada

- `GET /suppliers` respondio `200` tras el movimiento de ruta, confirmando que la API mantiene funcionalidad.
- Se verifico presencia del archivo en la nueva ubicacion `data/process/suppliers/suppliers.json`.

### Resultado

La estructura de `data/` queda mas ordenada por responsabilidad (raw/process/eval/pipelines) y los artefactos de ejecucion local quedan fuera de versionado para evitar ruido en commits.

## Actualizacion 2026-08-05 (Supplier Directory — frontend backoffice)

### Solicitud del cliente

Completar la parte faltante del hito 09 implementando en `uis/backoffice` la interfaz del directorio de proveedores conectada a la API ya construida.

### Cambios aplicados

- Se agrego la ruta `uis/backoffice/app/suppliers/page.tsx`.
- Se agrego acceso de navegacion **Suppliers** en `BackofficeShell.tsx`.
- Se implemento `SuppliersWorkspace` como orquestador de la pantalla:
  - carga desde `GET /suppliers`;
  - filtros en cliente por `country` y `category` sin recarga;
  - estados `loading`, error y vacio;
  - refresco visual tras crear o actualizar proveedores.
- Se creo `SupplierForm` con validacion cliente para:
  - nombre obligatorio;
  - al menos una categoria;
  - `monthly_rate > 0`;
  - email valido si se informa.
- Se creo cliente HTTP `lib/services/suppliersApi.ts` para:
  - `GET /suppliers`;
  - `POST /suppliers`;
  - `PATCH /suppliers/{id}/rate`;
  - `PATCH /suppliers/{id}/status`.
- Se agregaron tipos y constantes en `types/suppliers.ts`.
- Se agrego `SupplierStatusBadge` para diferenciar visualmente proveedores `active` y `suspended`.

### Validacion ejecutada

- `cd uis/backoffice && npm run build` → OK.
- La build genero correctamente la nueva ruta estatica `/suppliers`.

### Resultado

El backoffice ya permite visualizar y operar el Supplier Directory de HealthCore desde interfaz: listado, filtros, alta, cambio de tarifa y cambio de estado, conectado al backend FastAPI del hito.

## Actualizacion 2026-08-05 (refactor capas en `services/app`)

### Solicitud del cliente

Reorganizar el backend FastAPI en capas (`core`, `models`, `domain`, `routers`) sin romper contratos HTTP ni rutas de datos, y alinear documentacion operativa.

### Cambios aplicados

- Se reorganizo el backend en `services/app/` con:
  - `main.py` — entrypoint FastAPI + CORS;
  - `core/database.py` — TinyDB (`data/process/suppliers/suppliers.json`);
  - `core/seed.py` — seed idempotente de proveedores;
  - `models/supplier.py` — enums y modelos Pydantic;
  - `domain/supplier_service.py` — logica TinyDB de suppliers;
  - `domain/incident_service.py` — wrapper fino sobre `incidents_analysis`;
  - `routers/suppliers.py` y `routers/incidents.py` — solo HTTP.
- Se actualizo `pyproject.toml`: `seed = "services.app.core.seed:run_seed"`.
- Se actualizaron docs operativos: `services/README(.es).md`, `uis/backoffice/README(.es).md`, `memory-bank/progress.md`, `memory-bank/techContext.md`.
- Contratos HTTP sin cambio: `/suppliers`, `/api/incidents/analyze`, `/api/incidents/results/export`.
- `services/incidents_analysis/` sin cambios de layout ni de reglas.

### Comandos vigentes

```bash
python -m uvicorn services.app.main:app --reload
python -m services.app.core.seed
```

### Validacion ejecutada

- Import: `from services.app.main import app`.
- Seed idempotente (15 suppliers).
- `GET /suppliers` → 200.
- `POST /api/incidents/analyze` + `GET /api/incidents/results/export` → 200.
- Pipeline CLI vía `incidents_analysis`: 100 / 94 / 6 / satisfaction 3.58.

### Resultado

El backend queda en capas alineadas con la evolucion del monorepo, sin alterar la API consumida por el backoffice ni el CLI de incidentes.

## Actualizacion 2026-08-07 (AUTH-01 — autenticacion JWT, en progreso)

### Solicitud / hito

Implementar autenticacion JWT en la API HealthCore existente (rama `feature/auth`): users + profiles en TinyDB, login, `get_current_user`, y proteccion de rutas sensibles.

### Cambios aplicados

- Dependencias: `passlib[bcrypt]`, `bcrypt==4.0.1`, `python-jose[cryptography]`, `python-dotenv`.
- `.env` / `.env.example` en la raiz: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
- TinyDB auth: `data/process/auth/auth.json` (ignorado en git) — tablas `users` y `profiles`.
- Capas en `services/app/`:
  - `models/user.py`, `models/profile.py`
  - `domain/user_service.py` (CRUD + `authenticate_user`)
  - `domain/profile_service.py`
  - `core/security.py` (hash/verify + JWT)
  - `core/deps.py` (`OAuth2PasswordBearer`, `get_current_user`)
  - routers: `users.py`, `auth.py`, `profiles.py` registrados en `main.py`
- Endpoints:
  - `POST /users` (publico, crea User + Profile; password hasheada)
  - `GET/PUT/DELETE /users...` (CRUD completo; token aun no obligatorio en todas)
  - `POST /auth/login` → JWT
  - `GET /auth/me` (protegido; email, role, profile)
  - `GET/PUT /profiles/me` (protegido)
- User/Profile solo en TinyDB (sin tablas SQL de usuarios).

### Validacion manual

- Registro / listado / get / update / delete de users.
- Login JSON + `Authorization: Bearer <token>` → `GET /auth/me` 200.
- Nota: el boton Authorize de Swagger (flujo OAuth2 form `username`/`password`) no encaja con login JSON actual → 422; probar con curl o adaptar a `OAuth2PasswordRequestForm` mas adelante.
- Cuidado en Windows: varios procesos `uvicorn` en el puerto 8000 pueden servir codigo viejo; usar un solo server (`scripts/kill-uvicorn.ps1` si hace falta).

### Pendiente para cerrar AUTH-01

- Exigir token en `/users` excepto `POST /users`.
- Proteger al menos 5 rutas de suppliers/incidents.
- 403 cuando un no-admin modifica otro usuario.
- Confirmacion final 401 sin token / token invalido.

### Resultado parcial

Base de autenticacion operativa (~75–80% del hito). El backoffice aun no envia token; al proteger suppliers/incidents esas pantallas fallaran hasta la fase de frontend (esperado segun el enunciado).

## Actualizacion 2026-08-07 (AUTH-01 — proteccion de rutas y 403)

### Cambios

- `core/deps.py`: helper `require_self_or_admin`.
- `routers/users.py`: `GET/PUT/DELETE` con Bearer; PUT/DELETE solo dueño o admin; solo admin puede cambiar `role`.
- `routers/suppliers.py`: las 6 rutas exigen Bearer (cubre el minimo de 5 rutas fuera de `/users` y `/auth`).
- `POST /users` sigue publico. Incidents sin cambio (siguen publicas).

### Validacion esperada

- Sin token: `GET /suppliers` y `GET /users` → 401.
- Con token valido: esas rutas → 200.
- User no-admin `PUT /users/{otro_id}` → 403.
- `POST /users` sin token → 201.

### Resultado

AUTH-01 cerrado en backend respecto a proteccion de rutas. El backoffice de suppliers devolvera 401 hasta que envie el JWT.

## Actualizacion 2026-08-09 (AUTH-02 fases 1–2 — login/register frontend)

### Alcance

Backoffice (`uis/backoffice`) en rama `feature/auth-frontend`: ciclo de vida del token + vistas `/login` y `/register`. Sin guard de rutas ni profile/logout aún.

### Decision de estructura

Se eligió layout mínimo (`AppChrome` + páginas en `app/login` y `app/register`) en lugar de route groups `(auth)`/`(app)`, para no mover páginas existentes. Token y fetch viven en `lib/services/` (mismo patrón que suppliers/incidents), no en una carpeta `lib/auth/` nueva.

### Cambios

- `lib/services/healthcoreClient.ts`: `localStorage` (`healthcore_access_token`), Bearer en llamadas, 401 → clear + redirect `/login`.
- `lib/services/authApi.ts`: login (`username`=email), register, registerAndLogin.
- `app/login`, `app/register` + formularios; redirect a `/` tras éxito.
- `AppChrome`: login/register sin `BackofficeShell`.
- `suppliersApi` / `healthcoreApi` usan el cliente compartido (Bearer).
- `uis/website` sin cambios.

### Docs actualizadas

- `uis/backoffice/README(.es).md`, `uis/README(.es).md`
- `services/README(.es).md`
- `memory-bank/progress.md`, `memory-bank/techContext.md`
- esta bitácora

### Validacion

- `cd uis/backoffice && npm run build` — OK (rutas `/login`, `/register` generadas).

### Como probar manualmente

1. API HealthCore en `:8000` + `npm run dev` en `uis/backoffice`.
2. `/register` → cuenta nueva → debe redirigir a `/` y guardar token en `localStorage`.
3. Con sesión, `/suppliers` debe cargar (Bearer enviado).
4. Forzar 401 (borrar/alterar token) en una llamada protegida → clear + redirect `/login`.

### Pendiente AUTH-02

- Protección de rutas (AuthGuard).
- `/account/profile`.
- Logout en shell.

## Actualizacion 2026-08-09 (AUTH-02 fase 3 — guard de rutas)

### Cambios

- `AppChrome`: guard por presencia de token (`useSyncExternalStore` + redirects); sin `setState` en el effect (arregla lint React).
- Sin token en rutas internas → `/login`; con token en `/login` o `/register` → `/`.
- `RegisterForm`: campo confirmar contraseña + validación de coincidencia.
- Docs: `progress.md`, `techContext.md`, `uis/backoffice/README(.es).md`.

### Validacion

- Lint limpio en `AppChrome` / `RegisterForm`.
- `cd uis/backoffice && npm run build`.

### Pendiente AUTH-02

- `/account/profile`.
- Logout en shell.

## Actualizacion 2026-08-10 (AUTH-02 fases 4–5 — profile + logout)

### Cambios

- `/account/profile`: `GET /auth/me`, formulario editable → `PUT /profiles/me`.
- Nav Profile; botón **Cerrar sesión** en `BackofficeShell` → clear token + `/login`.
- Docs: progress, techContext, backoffice README(.es); AUTH-02 cerrado (fases 1–5).
- `data/process/auth/auth.json` ya estaba en `.gitignore` (sin cambio).

### Validacion

- `cd uis/backoffice && npm run build`.

### Resultado

AUTH-02 frontend cerrado: login/register, guard, profile, logout, Bearer + 401.

## Actualizacion 2026-08-11 (AUTH-03 — recuperacion y cambio de contraseña)

### Alcance

Rama `feature/password-reset`: forgot/reset por email (Resend) + change-password autenticado. API + backoffice. Website sin tocar.

### Decisiones

- Token de reset: cadena aleatoria con **estado en servidor** (TinyDB `password_reset_tokens`: hash SHA-256, `expires_at`, borrado tras uso / al emitir uno nuevo). Cumple uso único mejor que JWT puro sin denylist.
- Correo: **Resend** (no SendGrid). Remitente de prueba: `onboarding@resend.dev` (no `beth.t@example.com`; Resend responde 403 con dominio no verificado).
- Enlace del email apunta al **frontend** (`FRONTEND_BASE_URL/reset-password?token=...`), no al API.
- `POST /auth/forgot-password` siempre **200** (anti-enumeración); fallos de email se loguean en servidor.
- Windows local: TLS a Resend fallaba (`CERTIFICATE_VERIFY_FAILED`); se añadió `certifi` + `EMAIL_SSL_VERIFY=false` solo para desarrollo local.

### Backend

- `services/app/core/database.py`: tabla `password_reset_tokens`.
- `services/app/domain/password_reset_service.py`: crear/validar/invalidar token, envío Resend, change-password.
- `services/app/routers/auth.py`:
  - `POST /auth/forgot-password` `{ email }` → siempre 200
  - `POST /auth/reset-password` `{ token, new_password }` → 400 si inválido/expirado/usado
  - `POST /auth/change-password` `{ current_password, new_password }` (Bearer) → 400 si current incorrecta
- Modelos en `models/user.py`: `ForgotPasswordRequest`, `ResetPasswordRequest`, `ChangePasswordRequest`.
- Env (raíz `.env` / `.env.example`): `RESEND_API_KEY`, `EMAIL_FROM`, `FRONTEND_BASE_URL`, `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`, `PASSWORD_RESET_EMAIL_PROVIDER`, `EMAIL_SSL_VERIFY`. API key **nunca** en código fuente (solo `os.getenv`).

### Frontend (backoffice)

- Rutas públicas: `/forgot-password`, `/reset-password` (añadidas a `AppChrome` AUTH_PATHS y a `redirectToLogin` en `healthcoreClient`).
- `/account/change-password` (protegida) + nav **Change password**.
- Login: enlace “¿Olvidaste tu contraseña?”; mensaje de éxito con `?reset=success` (`searchParams` async).
- Forms: `ForgotPasswordForm`, `ResetPasswordForm` (+ `ResetPasswordTokenReader` + Suspense), `ChangePasswordForm`.
- `authApi.ts`: `forgotPassword` / `resetPassword` con `auth: false`; `changePassword` con Bearer.

### Docs tocadas

- `bitacora.md` (esta entrada)
- `memory-bank/progress.md`, `memory-bank/techContext.md`
- `services/README(.es).md`
- `uis/README(.es).md`
- `uis/backoffice/README(.es).md`
- `.env.example`

### Validacion

- Forgot email inexistente → 200; existente → 200 + email Resend (revisar Gmail/spam y dashboard Resend).
- Reset token inválido → 400; tras éxito → redirect `/login?reset=success`; token no reutilizable.
- Change-password sin Bearer → 401; current incorrecta → 400.
- `npx tsc --noEmit` en backoffice OK.
- `npm run build`: en este entorno falló por SSL al descargar Google Fonts (Inter); no por el código auth.

### Como probar manualmente

1. API en `:8000` con `.env` (Resend + `FRONTEND_BASE_URL` alineado al puerto de Next).
2. Usuario en DB con el **mismo email** de la cuenta Resend (restricción onboarding).
3. `/forgot-password` → mensaje genérico → abrir correo → `/reset-password?token=...` → login.
4. Con sesión: `/account/change-password`.

### Resultado

AUTH-03 cerrado: recuperación por email real, reset de un solo uso, cambio de contraseña autenticado, secretos solo en env.
