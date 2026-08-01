import csv
from pathlib import Path


def _summary_to_rows(summary: dict) -> list[dict]:
    rows: list[dict] = []

    rows.append({"metric": "total_records", "value": summary["total"], "percentage": ""})
    rows.append({"metric": "valid_records", "value": summary["valid"], "percentage": ""})
    rows.append({"metric": "invalid_records", "value": summary["invalid"], "percentage": ""})

    for rule, count in summary["invalid_breakdown"].items():
        rows.append({"metric": f"invalid.{rule}", "value": count, "percentage": ""})

    for name, data in summary["by_category"].items():
        rows.append({
            "metric": f"category.{name}",
            "value": data["count"],
            "percentage": data["percentage"],
        })

    for name, data in summary["by_status"].items():
        rows.append({
            "metric": f"status.{name}",
            "value": data["count"],
            "percentage": data["percentage"],
        })

    for name, data in summary["by_country"].items():
        rows.append({
            "metric": f"country.{name}",
            "value": data["count"],
            "percentage": data["percentage"],
        })

    sat = summary["satisfaction"]
    rows.append({
        "metric": "satisfaction.scored_cases",
        "value": sat["scored_cases"],
        "percentage": "",
    })
    rows.append({
        "metric": "satisfaction.average",
        "value": sat["average"],
        "percentage": "",
    })
    for score, count in sat["histogram"].items():
        rows.append({
            "metric": f"satisfaction.score_{score}",
            "value": count,
            "percentage": "",
        })

    return rows


def export_results(summary: dict, output_path: str | Path) -> Path:
    """Write analysis metrics to CSV (metric, value, percentage). No PHI."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = _summary_to_rows(summary)
    fieldnames = ["metric", "value", "percentage"]

    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return path