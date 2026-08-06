# Propuesta de Arquitectura de Backend

## Arquitectura Propuesta

Consideré usar una **Arquitectura Hexagonal** porque proporciona una clara separación entre la lógica de negocio y las tecnologías externas. Sin embargo, en la etapa actual de HealthCore, creo que introduciría una complejidad innecesaria.

Actualmente, el backend se centra en exponer una API REST, procesar el análisis de incidentes y dar soporte a las interfaces de usuario existentes. Dominios futuros como Pacientes, Citas, Facturación, Reclamaciones e Informes se incorporarán gradualmente, pero el sistema aún no requiere la cantidad de integraciones que justificarían una arquitectura hexagonal completa.

Por esta razón, propongo usar una **arquitectura por capas organizada por dominios de negocio**. Este enfoque mantiene el proyecto simple, mantenible y escalable, a la vez que permite su evolución hacia una arquitectura más avanzada si los requisitos futuros lo exigen.

--

# Propuesta de Estructura de Backend

El repositorio actual ya separa el backend en el directorio **services/**. En lugar de rediseñar esta estructura, propongo extenderla manteniendo los mismos principios de organización.

```
services/
│
├── app/
│   ├── main.py
│   ├── core/                    # database (TinyDB), seed
│   ├── models/                  # modelos Pydantic (p. ej. supplier)
│   ├── domain/                  # orquestacion de negocio
│   └── routers/
│       ├── incidents.py
│       ├── suppliers.py
│       ├── patients.py          (futuro)
│       ├── appointments.py      (futuro)
│       ├── billing.py           (futuro)
│       ├── claims.py            (futuro)
│       └── reports.py           (futuro)
│
├── incidents_analysis/
│   ├── analyzer.py
│   ├── csv_reader.py
│   ├── validator.py
│   ├── exporter.py
│   └── models.py
│
└── (placeholders de dominio: gateway, clinical-operations, revenue-cycle, compliance)
```

El proyecto actual ya demuestra una buena separación entre la capa de API y la lógica de análisis de incidentes. La evolución propuesta mantiene el mismo principio al permitir que nuevos dominios de negocio expongan sus propios endpoints, manteniendo su lógica de negocio aislada de la capa HTTP.

---

# Módulos

## app/

Contiene la aplicación FastAPI, organizada en capas:

- `main.py` — entrypoint, CORS, registro de routers
- `core/` — infraestructura compartida (TinyDB, seed)
- `models/` — modelos Pydantic
- `domain/` — orquestación de negocio (llama a paquetes como `incidents_analysis`)
- `routers/` — solo endpoints HTTP

Su función es exponer endpoints REST, validar las solicitudes entrantes y delegar el procesamiento a los módulos de negocio correspondientes.

Los enrutadores deben ser ligeros y evitar implementar lógica de negocio.

--

## incidents_analysis/

Contiene toda la lógica de negocio relacionada con el procesamiento de incidentes CSV.

Las responsabilidades actuales incluyen:

- lectura de archivos CSV;

- validación de su contenido;

- cálculo de métricas;

- exportación de resultados;

- definición de modelos de análisis.

Este módulo ya puede reutilizarse en diferentes puntos de entrada, como la herramienta de línea de comandos y la API REST, evitando así la duplicación de lógica.

--

## core/

Vive en `services/app/core/` y centraliza la infraestructura compartida del backend.

Actualmente incluye:

- inicializacion TinyDB del directorio de proveedores;
- script de seed de proveedores.

La configuracion de aplicacion / variables de entorno puede crecer aqui cuando haga falta. Evitar autenticacion o middleware hasta que existan esos requisitos.

---

## database/

Los adaptadores de persistencia viven por ahora en `app/core/` (TinyDB). Un paquete top-level `database/` solo deberia crearse si aparecen multiples backends o factories de conexion compartidas.

---

## Comun (futuro)

Este directorio solo se creara cuando se implementen componentes de backend reutilizables.

Su proposito es alojar utilidades compartidas por varios modulos, evitando implementaciones duplicadas y la creacion de codigo generico innecesario.

---

# Organización de puntos finales

Propongo organizar la API REST por dominios de negocio en lugar de por operaciones técnicas.

La implementación actual ya sigue esta idea a través del punto final de análisis de incidentes.

Los dominios futuros deben seguir utilizando la misma convención.

| Dominio | Puntos finales de ejemplo | Responsabilidad |

|----------|-----------------|----------------|

| Incidentes | GET /incidents<br>POST /incidents/analyze | Análisis de incidentes |

| Pacientes | GET /patients<br>POST /patients | Gestión de pacientes |

| Citas | GET /appointments<br>POST /appointments | Programación de citas |

| Facturación | GET /billing | Información de facturación |
| Reclamaciones | GET /claims | Reclamaciones de seguros |

| Informes | GET /reports | Paneles de control e informes empresariales |

Esta organización facilita la comprensión de la API, mantiene los endpoints relacionados agrupados y simplifica el mantenimiento futuro.

--

# Convenciones de FastAPI

Tras investigar las estructuras de proyectos FastAPI más comunes, observé que la mayoría de las aplicaciones separan las responsabilidades en enrutadores, lógica de negocio, modelos, esquemas y configuración.

Aunque FastAPI no impone una estructura de proyecto oficial, estas convenciones influyeron en mi propuesta.

En lugar de crear una organización completamente nueva, propongo adaptar estas prácticas al repositorio actual, manteniendo la capa de API independiente de los módulos de lógica de negocio y ampliando la estructura existente a medida que se añadan nuevos dominios.

--

# Organización del frontend y el backend

HealthCore utiliza un monorepo.
