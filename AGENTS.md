# AGENTS.md

## Project Mission
Build secure, compliant, and scalable digital systems for HealthCore's outpatient operations across the US and UK, aligned with business priorities in patient access, clinical workflows, billing, compliance, workforce, and executive visibility.

## Critical Restriction
- Ignore `company-choise.md` completely until a developer explicitly authorizes reading it.
- Treat similarly named files as restricted unless a developer explicitly confirms otherwise.

## Required Reading Order (Every New Session)
1. `memory-bank/techContext.md`
2. `memory-bank/progress.md`
3. `CONTEXT.md`
4. Relevant rule files in `.agents/rules/`

## Repository Overview
- `CONTEXT.md` is the business source of truth.
- `memory-bank/` stores persistent project and execution context for AI agents.
- `.agents/rules/` stores behavior and contribution policies.
- Implementation areas include `src/`, `uis/`, `services/`, `data/`, and supporting folders.

## Mandatory Workflow Before Coding
1. Confirm scope and allowed directories.
2. Read required context files in order.
3. Identify applicable rule files for the target task.
4. Validate whether the task is documentation-only or code-change eligible.
5. Ask for clarification if any requirement is ambiguous.

## Rules for Modifying Files
- Modify only files required by the task.
- Do not modify unrelated files.
- Do not rename files or folders without explicit developer approval.
- Do not create or delete folders without explicit developer approval.
- Preserve existing project conventions in every touched file.

## Validation Requirements
- Do not modify any non-documentation folder without explicit developer confirmation.
- Run relevant checks/tests when available for changed areas.
- If checks cannot be run, document that limitation explicitly in the delivery notes.

## Commit Expectations
- Keep commits small, scoped, and reviewable.
- Use clear commit messages describing what changed and why.
- Do not amend or rewrite history unless explicitly requested.

## Pull Request Expectations
- Include objective, scope, changed files summary, validation evidence, and known risks.
- Keep PRs focused; avoid unrelated changes.
- Add TODO follow-ups for any accepted gaps.

## Documentation Requirements
- Write in professional English.
- Use concise, scan-friendly Markdown.
- Add `TODO:` markers when information is missing.
- Do not invent business requirements not present in `CONTEXT.md`.
- Update `memory-bank/progress.md` after meaningful changes.

## Safety Rules
- Protect compliance-sensitive assumptions (HIPAA/UK GDPR context).
- Never fabricate sensitive data or unverifiable business facts.
- Stop immediately if instructions conflict with repository safety constraints.

## When to Stop and Ask for Clarification
- Missing or contradictory requirements.
- Requests that imply restructuring, renaming, or deleting assets without explicit approval.
- Tasks spanning multiple repository areas without clear scope boundaries.
- Any conflict between user request and repository governance rules.
