# Rule: Repository Structure

## Purpose
Define how AI agents must navigate and respect repository boundaries.

## Requirements
- Treat this repository as a multi-area project (UI, services, data, workflows, shared packages).
- Before editing, identify the smallest valid scope for the task.
- Keep changes local to the relevant area; do not perform cross-area edits unless explicitly requested.
- Do not introduce new top-level folders unless explicitly approved by a developer.
- Prefer existing documented locations for docs, rules, and context updates.

## Required Checks Before Changes
- Read `CONTEXT.md` for business alignment.
- Read `memory-bank/techContext.md` and `memory-bank/progress.md` first.
- Verify target file path belongs to the expected repository area.

## Out-of-Scope Handling
- If the task requires restructuring, stop and request explicit developer confirmation.
