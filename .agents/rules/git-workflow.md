# Rule: Git Workflow

## Purpose
Set minimum expectations for branch, commit, and PR behavior by AI agents.

## Commit Expectations
- Keep commits scoped to one logical change.
- Use clear commit messages describing what changed and why.
- Do not rewrite or amend existing commits unless explicitly requested.
- Never perform destructive history operations without explicit approval.

## Pull Request Expectations
- PR description must include:
  - Objective and scope.
  - Files changed summary.
  - Validation steps executed.
  - Risks and follow-up TODOs.
- Keep PRs focused and reviewable.

## Branch and Change Safety
- Do not revert unrelated user changes.
- If unrelated modifications are detected, isolate your changes and proceed safely.
- If conflict prevents safe progress, stop and ask for instructions.
