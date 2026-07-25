# Propocion de arquitectura Back-end

He considerado la **arquitectura hexagonal** por su capacidad para desacoplar la lógica de negocio de las tecnologías e integraciones externas. Sin embargo, en la fase actual de HealthCore el backend se centra principalmente en exponer una API REST, gestionar los dominios de pacientes, citas, facturación y reportes, y servir de soporte al frontend. En este contexto, una **arquitectura en capas** organizada por dominios ofrece un equilibrio adecuado entre simplicidad, mantenibilidad y escalabilidad. Además, esta organización permite evolucionar hacia una arquitectura hexagonal si en el futuro aumentan las integraciones y la complejidad del sistema

## Propuesta de arquitectura de carpetas y modulos

"Propongo una estructura modular organizada por dominios de negocio. Cada módulo agrupa sus routers, servicios, repositorios, modelos y esquemas relacionados, reduciendo el acoplamiento entre áreas funcionales. Los elementos compartidos, como la configuración, la conexión a la base de datos y las utilidades comunes, se ubican en carpetas independientes (**core, database y common**) para evitar duplicación de código y mantener responsabilidades bien definidas."

**Core** tendría la responsabilidad de centralizar la configuración global del backend, como la carga de variables de entorno y parámetros comunes de la aplicación. En la fase actual del proyecto no incluiría otros componentes como autenticación o middleware porque todavía no forman parte de los requisitos documentados.

**Database** agrupa todos los componentes relacionados con la persistencia de datos. Su objetivo es centralizar la configuración y el acceso a la base de datos para que los distintos módulos del sistema (Patients, Appointments, Billing, Claims, etc.) compartan una misma infraestructura de almacenamiento sin duplicar configuración. Además, esta separación facilita el mantenimiento y la evolución del sistema, ya que cualquier cambio relacionado con la persistencia puede realizarse en un único lugar sin afectar a la lógica de negocio de cada dominio.

**Common** estaría destinada únicamente a componentes reutilizables por varios módulos del backend. Su contenido crecería únicamente cuando aparezcan necesidades compartidas entre dominios, evitando duplicar código.

## organización de endpoints y ruters
