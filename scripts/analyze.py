import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.incidents_analysis.csv_reader import read_incidents
from services.incidents_analysis.validator import validate_incidents
from services.incidents_analysis.analyzer import analyze_incidents
from services.incidents_analysis.exporter import export_results


def print_report(summary: dict, source_name: str) -> None:
    inv = summary["invalid_breakdown"]
    cat = summary["by_category"]
    st = summary["by_status"]
    co = summary["by_country"]
    sat = summary["satisfaction"]

    print("=" * 60)
    print("  HEALTHCORE — PATIENT INCIDENT REPORT ANALYSIS")
    print(f"  Source file: {source_name}")
    print("=" * 60)
    print()
    print(f"TOTAL RECORDS IN FILE .......... {summary['total']}")
    print(f"  ├─ Valid records ................ {summary['valid']}")
    print(f"  └─ Invalid / incomplete .......... {summary['invalid']}")
    print()
    print("INVALID RECORDS BREAKDOWN")
    print(f"  ├─ Invalid or missing clinic_id .. {inv['invalid_clinic_id']}")
    print(f"  ├─ Country/clinic mismatch ....... {inv['country_clinic_mismatch']}")
    print(f"  ├─ Invalid or missing category ... {inv['invalid_category']}")
    print(f"  ├─ Empty description ............. {inv['empty_description']}")
    print(f"  ├─ Missing patient_id ............ {inv['missing_patient_id']}")
    print(f"  └─ Closed case, no score ......... {inv['closed_without_score']}")
    print()
    print("BREAKDOWN BY CATEGORY (valid records)")
    print(
        f"  ├─ APPOINTMENT .................. {cat['APPOINTMENT']['count']}  "
        f"({cat['APPOINTMENT']['percentage']}%)"
    )
    print(
        f"  ├─ BILLING ...................... {cat['BILLING']['count']}  "
        f"({cat['BILLING']['percentage']}%)"
    )
    print(
        f"  ├─ CLINICAL_CARE ................ {cat['CLINICAL_CARE']['count']}  "
        f"({cat['CLINICAL_CARE']['percentage']}%)"
    )
    print(
        f"  ├─ ACCESSIBILITY ................ {cat['ACCESSIBILITY']['count']}  "
        f"({cat['ACCESSIBILITY']['percentage']}%)"
    )
    print(
        f"  └─ ADMINISTRATIVE ............... {cat['ADMINISTRATIVE']['count']}  "
        f"({cat['ADMINISTRATIVE']['percentage']}%)"
    )
    print()
    print("BREAKDOWN BY STATUS (valid records)")
    print(
        f"  ├─ OPEN ......................... {st['OPEN']['count']}  "
        f"({st['OPEN']['percentage']}%)"
    )
    print(
        f"  ├─ CLOSED ....................... {st['CLOSED']['count']}  "
        f"({st['CLOSED']['percentage']}%)"
    )
    print(
        f"  └─ DISCARDED .................... {st['DISCARDED']['count']}  "
        f"({st['DISCARDED']['percentage']}%)"
    )
    print()
    print("BREAKDOWN BY COUNTRY (valid records)")
    print(
        f"  ├─ US ........................... {co['US']['count']}  "
        f"({co['US']['percentage']}%)"
    )
    print(
        f"  └─ UK ........................... {co['UK']['count']}  "
        f"({co['UK']['percentage']}%)"
    )
    print()
    print("SATISFACTION INDEX (closed cases)")
    print(f"  Scored cases: {sat['scored_cases']} of {st['CLOSED']['count']}")
    print(f"  Average score: {sat['average']} / 5.00")
    hist = sat["histogram"]
    print(f"  ├─ Score 1 (Very dissatisfied) ... {hist[1]}")
    print(f"  ├─ Score 2 (Dissatisfied) ........ {hist[2]}")
    print(f"  ├─ Score 3 (Neutral) ............ {hist[3]}")
    print(f"  ├─ Score 4 (Satisfied) .......... {hist[4]}")
    print(f"  └─ Score 5 (Very satisfied) ...... {hist[5]}")
    print()
    print("=" * 60)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze.py <path-to-csv>", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    try:
        incidents = read_incidents(csv_path)
        valid, invalid_counts = validate_incidents(incidents)
        summary = analyze_incidents(valid, invalid_counts, total=len(incidents))
    except (OSError, UnicodeDecodeError, KeyError, ValueError) as exc:
        print(f"Failed to read or parse CSV: {exc}", file=sys.stderr)
        sys.exit(1)

    print_report(summary, source_name=csv_path.name)

    answer = input("Export results to CSV? [y / n]: ").strip().lower()
    if answer == "y":
        out = ROOT / "data" / "process" / "results.csv"
        try:
            export_results(summary, out)
        except OSError as exc:
            print(f"Failed to export results: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"Exported to {out}")
    else:
        print("Export skipped.")


if __name__ == "__main__":
    main()
