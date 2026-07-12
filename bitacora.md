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
Se obtuvo contenido publico de referencia de https://www.health-core.org/ via lectura en texto para construir copy base (servicios, vision, mision, valores y enfoque regional).

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
	- En `collections.ts`, `compareValues(...)` contempla `null` y `undefined`.
	- En validaciones, `phone` y `email` opcionales se manejan de forma segura.
- Riesgo residual:
	- Si en runtime llegan `null` en campos que TypeScript tipa como `string`/`array` obligatorios (por ejemplo `invoice.billingCodes` o `patient.fullName`), algunas validaciones podrian fallar por acceso directo (`.trim()`, `.length`) antes de construir errores de negocio.

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

- Documentación: https://playground.4geeks.com/tracker/api/v1/docs
- Base URL: `https://playground.4geeks.com/tracker/api/v1`
- Recurso principal: `/records` (sin namespace; distinto al patrón inicial de `/applications/{namespace}` del plan)

| Operación | Endpoint | Uso en UI |
|-----------|----------|-----------|
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
```
Abrir http://localhost:3000 → `/applications`.

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


## Texto fijo (NO BORRAR, MANTENER COMO FOOTER): comando de test para `models.ts`

### Objetivo
Validar rapidamente los tipos de `src/types/models.ts` y su archivo de pruebas de tipos.

### Comando fijo recomendado
Ejecutar desde `packages/shared`:

```bash
npm run test:types:models
```

### Paso a paso para principiantes
1. Abrir terminal en la raiz del proyecto.
2. Entrar a la carpeta del paquete:
	- `cd /workspaces/ocielgallardo-company-choice/packages/shared`
3. Ejecutar el test:
	- `npm run test:types:models`
4. Resultado esperado:
	- Si no aparece ningun error TypeScript, la validacion paso correctamente.

### Comando equivalente (referencia)
```bash
npx -y -p typescript tsc --noEmit ../../src/types/models.ts ../../src/types/models.type-test.ts --strict
```

