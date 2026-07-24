# Propocion de arquitectura Back-end

He considerado la arquitectura hexagonal por su capacidad para desacoplar la lógica de negocio de las tecnologías e integraciones externas. Sin embargo, en la fase actual de HealthCore el backend se centra principalmente en exponer una API REST, gestionar los dominios de pacientes, citas, facturación y reportes, y servir de soporte al frontend. En este contexto, una arquitectura en capas organizada por dominios ofrece un equilibrio adecuado entre simplicidad, mantenibilidad y escalabilidad. Además, esta organización permite evolucionar hacia una arquitectura hexagonal si en el futuro aumentan las integraciones y la complejidad del sistema

## Propuesta de arquitectura de carpetas
