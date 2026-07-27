# Propocion de arquitectura Back-end

He considerado la **arquitectura hexagonal** por su capacidad para desacoplar la lógica de negocio de las tecnologías e integraciones externas. Sin embargo, en la fase actual de HealthCore el backend se centra principalmente en exponer una API REST, gestionar los dominios de pacientes, citas, facturación y reportes, y servir de soporte al frontend. En este contexto, una **arquitectura en capas** organizada por dominios ofrece un equilibrio adecuado entre simplicidad, mantenibilidad y escalabilidad. Además, esta organización permite evolucionar hacia una arquitectura hexagonal si en el futuro aumentan las integraciones y la complejidad del sistema

## Propuesta de arquitectura de carpetas y modulos

"Propongo una estructura modular organizada por dominios de negocio. Cada módulo agrupa sus routers, servicios, repositorios, modelos y esquemas relacionados, reduciendo el acoplamiento entre áreas funcionales. Los elementos compartidos, como la configuración, la conexión a la base de datos y las utilidades comunes, se ubican en carpetas independientes (**core, database y common**) para evitar duplicación de código y mantener responsabilidades bien definidas."

**Core** tendría la responsabilidad de centralizar la configuración global del backend, como la carga de variables de entorno y parámetros comunes de la aplicación. En la fase actual del proyecto no incluiría otros componentes como autenticación o middleware porque todavía no forman parte de los requisitos documentados.

**Database** agrupa todos los componentes relacionados con la persistencia de datos. Su objetivo es centralizar la configuración y el acceso a la base de datos para que los distintos módulos del sistema (Patients, Appointments, Billing, Claims, etc.) compartan una misma infraestructura de almacenamiento sin duplicar configuración. Además, esta separación facilita el mantenimiento y la evolución del sistema, ya que cualquier cambio relacionado con la persistencia puede realizarse en un único lugar sin afectar a la lógica de negocio de cada dominio.

**Common** estaría destinada únicamente a componentes reutilizables por varios módulos del backend. Su contenido crecería únicamente cuando aparezcan necesidades compartidas entre dominios, evitando duplicar código.

## Organización de endpoints y ruters

Propongo que al igual que la API del Talent Pipeline Tracker organizaba sus recursos alrededor de un dominio (records), el backend de HealthCore organice sus endpoints alrededor de los dominios del negocio (patients, appointments, billing, claims, reports). Esa decisión hace que la API sea más consistente, fácil de navegar y más sencilla de mantener conforme crezca el proyecto.

## Estructura en FastApi

Tras investigar las estructuras más habituales en proyectos FastAPI, observé que es común separar responsabilidades como routers, servicios, modelos, esquemas y configuración para mejorar la organización y el mantenimiento del código. Aunque FastAPI no impone una estructura oficial, estas convenciones sirvieron como base para mi propuesta. En el caso de HealthCore, decidí adaptarlas organizando el backend por dominios de negocio (Patients, Appointments, Billing, Claims y Reports), ya que esta organización refleja mejor la estructura funcional del proyecto y facilita su crecimiento y mantenimiento a largo plazo.

## Organizacion de la App

En una arquitectura con frontend y backend separados, ambas aplicaciones funcionan de forma independiente y se comunican mediante una API REST. El frontend se encarga de la interfaz de usuario y realiza peticiones HTTP al backend, mientras que el backend concentra la lógica de negocio y el acceso a la base de datos. Cada aplicación mantiene sus propias variables de entorno y configuración, y la comunicación entre ambas requiere configurar CORS cuando se ejecutan en orígenes distintos. En el caso de HealthCore, considero adecuado mantener el enfoque de monorepo ya existente, incorporando el backend como un módulo independiente que pueda ser consumido tanto por la web pública como por el backoffice, favoreciendo la reutilización y el mantenimiento del proyecto.

## Puntos de Atencion 🛐

### Riesgo 1. Mezclar responsabilidades

Si la lógica de negocio se implementa directamente en los routers, cada endpoint terminará haciendo demasiado trabajo.

Consecuencias:

código difícil de mantener;
lógica duplicada;
cambios más propensos a introducir errores.

Justificación: la responsabilidad del router debería ser recibir la petición y delegar el trabajo a la capa de servicios.

### Riesgo 2. No organizar el backend por dominios

Si todos los endpoints, modelos y servicios se concentran en pocos archivos o carpetas generales, el proyecto será cada vez más difícil de entender conforme se añadan módulos como Patients, Billing o Reports.

Consecuencias:

mayor dificultad para localizar el código;
más conflictos entre desarrolladores;
mantenimiento más complejo.

### Riesgo 3. Duplicación de lógica

Si cada módulo implementa sus propias validaciones o consultas similares sin reutilizar componentes, aparecerá código duplicado.

Consecuencias:

más tiempo de mantenimiento;
inconsistencias entre módulos;
mayor probabilidad de errores.

### Riesgo 4. Acoplamiento excesivo

Si los módulos dependen demasiado unos de otros, un cambio en Patients podría afectar a Billing o Reports.

Consecuencias:

cambios más arriesgados;
pruebas más complicadas;
menor capacidad para evolucionar el sistema.
