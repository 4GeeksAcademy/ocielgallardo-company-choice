# Rule: TypeScript Guidelines

## Purpose
Define guardrails for TypeScript modeling and utility logic.

## Type Modeling
- Prefer explicit interfaces/types for domain entities.
- Keep model definitions centralized where possible.
- Avoid `any` unless absolutely unavoidable and documented.

## Functions and Utilities
- Keep utilities deterministic and side-effect aware.
- Validate inputs before processing business records.
- Return typed results and avoid implicit shape changes.

## Error and Validation Strategy
- Surface validation failures with clear and actionable messages.
- Encode business baselines only when documented in `CONTEXT.md`.

## Quality Check
- Run available type checks before finalizing TypeScript changes.
- If type checks cannot be run, clearly report that gap in delivery notes.
