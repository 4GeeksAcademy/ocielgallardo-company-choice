# `packages/shared`

Shared libraries used by more than one HealthCore deliverable.

## Contents

### TypeScript (`@repo/shared-types`)

- `package.json` / `types/` — shared TS placeholders and type-check scripts pointing at root `src/` models where configured.

### Python (`healthcore_shared`)

Import path: `healthcore_shared` (add `packages/shared` to `PYTHONPATH`, or rely on hatch `dev-mode-dirs` after install).

| Module | Role |
| --- | --- |
| `csv_validation.py` | Analyzer CSV invalidity rules (clinics, categories, description, patient_id pattern, CLOSED score) |
| `manager_constants.py` | Incident-manager branches, categories, origins, statuses, lifecycle transitions |
| `seed_mapping.py` | CSV → manager field transforms (`origin=customer`, clinic→branch, status/category maps) |
| `manager_validation.py` | Create/status field errors as `{field, message}` |

**Consumers**

- `scripts/seed_incidents.py`
- `services/incidents_analysis/validator.py` (re-export)
- `services/app/domain/incident_manager_service.py`

**Contract:** `docs/incident-manager/CONTEXT-HealthCore.md` and `docs/data-contract/CONTEXT-HealthCore.md` (CSV rules).

```bash
# from repo root
PYTHONPATH=packages/shared uv run python -c "import healthcore_shared; print('ok')"
```
