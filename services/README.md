# services

This folder contains backend service boundaries for the monorepo architecture.

## Purpose

- Keep backend concerns independent from UI applications.
- Enable future APIs to evolve as separate deployable units.
- Make domain ownership explicit by service area.

## Current architecture placeholders

- `_template-service/` blueprint for creating a new service.
- `gateway/` edge and cross-cutting backend concerns.
- `clinical-operations/` appointments and clinical workflow services.
- `revenue-cycle/` billing and claims services.
- `compliance/` governance and audit services.

## Implemented (Python, reusable by CLI / future API)

- `incidents_analysis/` — HealthCore patient incident CSV analysis (`models`, `csv_reader`, `validator`, `analyzer`, `exporter`). Consumed by `scripts/analyze.py`.

## Status

Incident analysis CLI logic lives under `incidents_analysis/`. HTTP APIs for other domains are still placeholders.

> Spanish version: [README.es.md](./README.es.md).
