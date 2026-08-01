import csv
from pathlib import Path

from .models import Incident


def _parse_satisfaction_score(raw: str | None) -> int | None:
    """Empty cell -> None. Non-empty -> int (validator will check 1-5 later)."""
    if raw is None:
        return None
    value = raw.strip()
    if value == "":
        return None
    return int(value)


def read_incidents(path: str | Path) -> list[Incident]:
    """Read a UTF-8 comma-separated incidents CSV into Incident objects.

    Does not validate business rules and must not print patient_id.
    """
    incidents: list[Incident] = []

    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            incidents.append(
                Incident(
                    incident_id=row["incident_id"],
                    date=row["date"],
                    clinic_id=row["clinic_id"],
                    country=row["country"],
                    category=row["category"],
                    description=row["description"],
                    status=row["status"],
                    patient_id=row["patient_id"],
                    satisfaction_score=_parse_satisfaction_score(
                        row.get("satisfaction_score")
                    ),
                )
            )

    return incidents