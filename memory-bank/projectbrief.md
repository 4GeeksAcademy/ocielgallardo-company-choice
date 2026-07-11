# Project Brief

## Mission
HealthCore builds internal digital systems to modernize outpatient care operations across a 12-clinic network in the United States and the United Kingdom.

## Why This Project Exists
HealthCore has grown operationally, but its technology landscape is fragmented across disconnected systems (EHRs, scheduling, billing, and manual spreadsheets). This project exists to create a unified, secure, and scalable foundation for clinical, operational, financial, and workforce workflows.

## Business Objectives
- Reduce patient no-show rates (current documented baseline: 22%).
- Reduce invoice claim rejection rates (current documented baseline: 14%).
- Improve cross-clinic operational visibility for executives and department leaders.
- Reduce clinical administrative burden (including documentation overhead).
- Strengthen compliance operations for HIPAA (US) and UK GDPR (UK).

## Product Vision
Deliver a modern healthcare operations platform that combines:
- Unified data access across departments and countries.
- Domain-specific operational dashboards.
- AI-assisted workflows (documentation, risk prediction, coding suggestions, support automation).
- Compliance-aware processes by design.

## Current Implementation Scope
Based on repository state and documented progress:
- Milestone 1 (Web): Corporate pages and application form implemented.
- Core Milestone 2 (Programming): TypeScript domain models and utility modules implemented.
- Manual utility playground implemented for browser testing.
- Type-level validation command available for shared models.

## Future Vision (Documented Direction)
- Unified online scheduling and patient engagement platform.
- Predictive no-show management workflow.
- AI-assisted revenue cycle quality controls.
- Compliance observability and audit automation.
- HR process automation and workforce analytics.
- Executive unified KPI dashboard with near real-time metrics.

## Main Business Entities
- Company
- Department
- Clinic/Location
- Patient
- Appointment
- Invoice/Claim
- No-show Prediction
- Critical Alert
- Workforce Records (hiring/training context)

## High-Level Architecture (Target Direction)
- Frontend interfaces for patient-facing and internal workflows.
- Shared typed domain model package.
- Utility layer for search, filtering, transformations, and validations.
- Future backend/API and workflow orchestration layers (planned in milestone roadmap).

## Development Philosophy
- Domain-first modeling aligned to business context.
- Strong typing and explicit validation rules.
- Incremental milestone delivery.
- Compliance and data protection as first-class constraints.
- Documentation-driven onboarding for AI and human contributors.

## Current Project Status
- Active educational/company-simulation implementation.
- Working code exists in web and TypeScript utility layers.
- Agent governance and context documentation being formalized.

## Known Assumptions
- The single source of truth for business context is CONTEXT.md.
- If business details are missing from CONTEXT.md, contributors must add TODO notes instead of assumptions.
- `company-choise.md` is intentionally out of scope unless explicitly authorized by a developer.
