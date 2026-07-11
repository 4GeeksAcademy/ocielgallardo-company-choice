# Rule: Coding Standards

## Purpose
Define behavioral standards for AI-generated code changes.

## Requirements
- Align all implementation decisions with business context from `CONTEXT.md`.
- Prefer explicit, readable, and maintainable code.
- Keep functions focused and avoid hidden side effects.
- Preserve existing project style in touched files.
- Avoid broad refactors unless explicitly requested.

## Safety Constraints
- Do not modify business logic outside the requested scope.
- Do not alter project configuration without explicit approval.
- If requirements are ambiguous, stop and ask for clarification.

## Quality Expectations
- Prioritize correctness over cleverness.
- Keep public behavior stable unless change is requested.
- Add minimal comments only where logic is non-obvious.
