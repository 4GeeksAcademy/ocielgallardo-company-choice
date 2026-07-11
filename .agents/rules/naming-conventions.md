# Rule: Naming Conventions

## Purpose
Ensure predictable naming for files, symbols, and documentation artifacts.

## General Rules
- Use descriptive, domain-aligned names.
- Prefer full words over unclear abbreviations.
- Keep naming consistent with existing project patterns.

## File Naming
- Documentation files: kebab-case (`example-rule.md`).
- TypeScript symbols: PascalCase for types/interfaces/classes, camelCase for functions/variables.
- Constants: UPPER_SNAKE_CASE only when project style uses it.

## Domain Naming
- Reuse business terms from `CONTEXT.md` (e.g., Appointment, Invoice, NoShowPrediction, CriticalAlert).
- Avoid introducing synonyms for existing entities unless explicitly requested.
