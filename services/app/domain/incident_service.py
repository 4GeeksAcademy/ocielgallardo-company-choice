"""Incident analysis orchestration for the HTTP API.

Business rules live in services.incidents_analysis; this module only wires them.
"""
from pathlib import Path
import tempfile

from services.incidents_analysis.csv_reader import read_incidents
from services.incidents_analysis.validator import validate_incidents
from services.incidents_analysis.analyzer import analyze_incidents
from services.incidents_analysis.exporter import export_results

ROOT = Path(__file__).resolve().parents[3]
RESULTS_CSV = ROOT / "data" / "process" / "results.csv"


def analyze_csv_bytes(content: bytes) -> dict:
    """Run the incidents pipeline on uploaded CSV bytes and persist results."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        incidents = read_incidents(tmp_path)
        valid, invalid_counts = validate_incidents(incidents)
        summary = analyze_incidents(valid, invalid_counts, total=len(incidents))
        export_results(summary, RESULTS_CSV)
        return summary
    finally:
        tmp_path.unlink(missing_ok=True)


def results_csv_path() -> Path:
    """Return the path to the last analysis export CSV."""
    return RESULTS_CSV
