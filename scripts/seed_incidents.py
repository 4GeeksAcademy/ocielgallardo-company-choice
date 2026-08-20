"""Idempotent seed of historical customer incidents from the analyzer CSV."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

# Ensure packages/shared is importable when run as `python scripts/seed_incidents.py`
_ROOT = Path(__file__).resolve().parents[1]
_SHARED = _ROOT / "packages" / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from healthcore_shared.csv_validation import validate_incidents  # noqa: E402
from healthcore_shared.seed_mapping import map_csv_incident_to_manager  # noqa: E402
from services.app.domain.incident_manager_service import (  # noqa: E402
    get_incident_summary,
    insert_seed_incident,
)
from services.incidents_analysis.csv_reader import read_incidents  # noqa: E402


def _resolve_csv_path(explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")
        return path

    candidates = [
        _ROOT / "data" / "raw" / "incidents-healthcore.csv",
        _ROOT / "scripts" / "incidents-healthcore.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find incidents-healthcore.csv under data/raw/ or scripts/"
    )


def run_seed(csv_path: str | None = None) -> int:
    path = _resolve_csv_path(csv_path)
    print(f"Seeding incidents from: {path}")

    rows = read_incidents(path)
    valid, invalid_counts = validate_incidents(rows)

    inserted = 0
    skipped_existing = 0
    skipped_unmapped = 0
    unmapped_reasons: list[str] = []

    for incident in valid:
        draft = map_csv_incident_to_manager(incident)
        if draft is None:
            skipped_unmapped += 1
            unmapped_reasons.append(
                getattr(incident, "incident_id", None) or "(missing incident_id)"
            )
            continue

        new_id = insert_seed_incident(draft)
        if new_id is None:
            skipped_existing += 1
        else:
            inserted += 1

    print("\n=== Seed report ===")
    print(f"CSV rows read:           {len(rows)}")
    print(f"Valid (analyzer rules):  {len(valid)}")
    print(f"Inserted:                {inserted}")
    print(f"Skipped (already exist): {skipped_existing}")
    print(f"Skipped (unmapped):      {skipped_unmapped}")

    print("\nInvalid rows (not inserted):")
    total_invalid = 0
    for reason, count in sorted(invalid_counts.items()):
        if count:
            print(f"  - {reason}: {count}")
            total_invalid += count
    if total_invalid == 0:
        print("  (none)")

    if unmapped_reasons:
        print("\nUnmapped valid rows (discarded):")
        for item in unmapped_reasons[:20]:
            print(f"  - {item}")
        if len(unmapped_reasons) > 20:
            print(f"  … and {len(unmapped_reasons) - 20} more")

    summary = get_incident_summary()
    print("\n=== Current /api/incidents/summary snapshot ===")
    print(f"Total: {summary.total}")
    print("By status:", dict(sorted(summary.by_status.items())))
    print("By category:", dict(sorted(summary.by_category.items())))
    print("By origin:", dict(sorted(summary.by_origin.items())))
    print("By branch:", dict(sorted(summary.by_branch.items())))

    # Helpful CONTEXT cross-check for non-zero categories after first full seed
    if summary.total:
        top_branches = Counter(
            {k: v for k, v in summary.by_branch.items() if v > 0}
        ).most_common()
        print("\nNon-zero branches (desc):", top_branches)

    return 0


def main() -> None:
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(run_seed(csv_arg))


if __name__ == "__main__":
    main()
