# Backend Architecture Proposal

## Proposed Architecture

I considered using **Hexagonal Architecture** because it provides a strong separation between business logic and external technologies. However, based on the current stage of HealthCore, I believe it would introduce unnecessary complexity.

At the moment, the backend is focused on exposing a REST API, processing incident analysis, and supporting the existing user interfaces. Future domains such as Patients, Appointments, Billing, Claims and Reports will gradually be incorporated, but the system does not yet require the number of integrations that would justify a fully hexagonal architecture.

For this reason, I propose using a **layered architecture organized by business domains**. This approach keeps the project simple, maintainable and scalable while allowing it to evolve toward a more advanced architecture if future requirements demand it.

---

# Backend Structure Proposal

The current repository already separates the backend under the **services/** directory. Rather than redesigning this structure, I propose extending it while maintaining the same organization principles.

```
services/
│
├── api/
│   ├── main.py
│   └── routers/
│       ├── incidents.py
│       ├── patients.py          (future)
│       ├── appointments.py      (future)
│       ├── billing.py           (future)
│       ├── claims.py            (future)
│       └── reports.py           (future)
│
├── incidents_analysis/
│   ├── analyzer.py
│   ├── csv_reader.py
│   ├── validator.py
│   ├── exporter.py
│   └── models.py
│
├── core/                        (future)
│
├── database/                    (future)
│
└── common/                      (future, only if shared components appear)
```

The current project already demonstrates a good separation between the API layer and the incident analysis logic. The proposed evolution keeps the same principle by allowing new business domains to expose their own endpoints while keeping their business logic isolated from the HTTP layer.

---

# Modules

## api/

Contains the FastAPI application.

Its responsibility is to expose REST endpoints, validate incoming requests and delegate processing to the corresponding business modules.

The routers should remain lightweight and avoid implementing business logic.

---

## incidents_analysis/

Contains all the business logic related to CSV incident processing.

Current responsibilities include:

- reading CSV files;
- validating their contents;
- calculating metrics;
- exporting results;
- defining analysis models.

This module can already be reused by different entry points, such as the command-line tool and the REST API, avoiding duplicated logic.

---

## core (future)

This module would centralize the backend configuration.

Initially it would only contain:

- application configuration;
- environment variable loading;
- shared configuration values.

I would avoid including authentication or middleware until those requirements exist.

---

## database (future)

Responsible for database configuration and persistence.

Keeping this responsibility isolated allows every business module to share the same database configuration without duplicating code.

---

## common (future)

This directory should only be created when reusable backend components actually appear.

Its purpose would be to host utilities shared by multiple modules, avoiding duplicated implementations while preventing the creation of unnecessary generic code.

---

# Endpoint Organization

I propose organizing the REST API by business domains instead of technical operations.

The current implementation already follows this idea through the incident analysis endpoint.

Future domains should continue using the same convention.

| Domain | Example Endpoints | Responsibility |
|----------|-----------------|----------------|
| Incidents | GET /incidents<br>POST /incidents/analyze | Incident analysis |
| Patients | GET /patients<br>POST /patients | Patient management |
| Appointments | GET /appointments<br>POST /appointments | Appointment scheduling |
| Billing | GET /billing | Billing information |
| Claims | GET /claims | Insurance claims |
| Reports | GET /reports | Dashboards and business reports |

This organization makes the API easier to understand, keeps related endpoints together and simplifies future maintenance.

---

# FastAPI Conventions

After researching common FastAPI project structures, I observed that most applications separate responsibilities into routers, business logic, models, schemas and configuration.

Although FastAPI does not impose an official project structure, these conventions influenced my proposal.

Rather than creating a completely new organization, I propose adapting these practices to the current repository by keeping the API layer independent from the business logic modules and expanding the existing structure as new domains are added.

---

# Frontend and Backend Organization

HealthCore follows a monorepo approach.

The user interfaces live inside the **uis/** directory, while the backend lives inside **services/**.

The backend exposes a REST API consumed by both user interfaces without allowing direct access to the business logic or persistence layer.

Each application maintains its own configuration and environment variables, while communication between frontend and backend occurs through HTTP requests. Because both applications run independently, CORS configuration will be required whenever they are executed under different origins.

This separation improves maintainability and allows both frontend applications to evolve independently while sharing the same backend services.

---

# Risks

## Mixing responsibilities

If business logic is implemented directly inside the API routers, endpoints will become difficult to maintain and reuse.

The router should only receive the request and delegate the processing to the corresponding business module.

---

## Poor domain organization

If all endpoints and business logic are concentrated in a few files, the project will become increasingly difficult to maintain as new domains are incorporated.

---

## Code duplication

Duplicating validation or processing logic across different modules increases maintenance costs and the probability of inconsistent behavior.

Reusable logic should remain isolated whenever possible.

---

## Strong coupling

Modules should remain as independent as possible.

Reducing dependencies between business domains makes future modifications safer and simplifies testing.