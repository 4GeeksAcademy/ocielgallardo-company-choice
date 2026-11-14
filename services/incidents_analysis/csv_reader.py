import csv
from io import StringIO
from pathlib import Path

from .models import Incident

REQUIRED_COLUMNS: tuple[str, ...] = (
    "incident_id",
    "date",
    "clinic_id",
    "country",
    "category",
    "description",
    "status",
    "patient_id",
)


class IncidentCsvError(ValueError):
    """Structural CSV problem safe to show to the user (no PHI)."""


def _parse_satisfaction_score(raw: str | None) -> int | None:
    """Empty cell -> None. Non-empty -> int (validator will check 1-5 later)."""
    if raw is None:
        return None
    value = raw.strip()
    if value == "":
        return None
    return int(value)


def _decode_csv_bytes(raw: bytes) -> str:
    """Decode UTF-8 (BOM optional). Reject empty files and other encodings."""
    if not raw:
        raise IncidentCsvError("The CSV file is empty.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IncidentCsvError("The CSV file must be UTF-8 encoded.") from exc
    if not text.strip():
        raise IncidentCsvError("The CSV file is empty.")
    return text


def _text_without_leading_blank_lines(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        raise IncidentCsvError("The CSV file is empty.")
    return "\n".join(lines) + "\n"


def _require_header(fieldnames: list[str] | None) -> list[str]:
    if not fieldnames:
        raise IncidentCsvError("The CSV file has no header row.")
    headers = [(name or "").strip() for name in fieldnames]
    if not any(headers):
        raise IncidentCsvError("The CSV file has no header row.")
    present = {name for name in headers if name}
    missing = [column for column in REQUIRED_COLUMNS if column not in present]
    if missing:
        raise IncidentCsvError(
            "The CSV is missing required columns: " + ", ".join(missing) + "."
        )
    return headers


def read_incidents_from_bytes(raw: bytes) -> list[Incident]:
    """Parse incidents CSV bytes. Raises IncidentCsvError for structural issues."""
    return _parse_incidents_csv(_decode_csv_bytes(raw))


def _parse_incidents_csv(text: str) -> list[Incident]:
    """Read a UTF-8 comma-separated incidents CSV into Incident objects.

    Does not validate business rules and must not print patient_id.
    """
    stream = StringIO(_text_without_leading_blank_lines(text))
    reader = csv.DictReader(stream)
    reader.fieldnames = _require_header(reader.fieldnames)

    incidents: list[Incident] = []
    try:
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
    except csv.Error as exc:
        # Never include row contents: they may hold patient_id (PHI).
        raise IncidentCsvError("The CSV file could not be parsed.") from exc

    return incidents


def read_incidents(path: str | Path) -> list[Incident]:
    """Read a UTF-8 comma-separated incidents CSV into Incident objects.

    Does not validate business rules and must not print patient_id.
    """
    return read_incidents_from_bytes(Path(path).read_bytes())
