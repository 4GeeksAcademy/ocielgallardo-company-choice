# Rule: File Modification Policy

## Purpose
Control what AI agents may or may not modify.

## Mandatory Policy
- Modify only files required by the requested task.
- Do not create, rename, or delete folders unless explicitly approved.
- Do not rename files unless explicitly approved.
- Do not touch generated files unless the task requires regeneration.
- Keep unrelated files unchanged.

## Explicit Restriction
- Ignore `company-choise.md` completely until a developer explicitly authorizes reading or editing it.

## Validation Gate
- Before editing any non-documentation folder, obtain explicit developer confirmation.
- If confirmation is not present, stop and ask.

## Documentation-Only Tasks
- During documentation-only requests, avoid all source code and configuration changes.
