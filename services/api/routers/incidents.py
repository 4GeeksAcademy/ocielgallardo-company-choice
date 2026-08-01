from pathlib import Path
import tempfile

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

from services.incidents_analysis.csv_reader import read_incidents
from services.incidents_analysis.validator import validate_incidents
from services.incidents_analysis.analyzer import analyze_incidents
from services.incidents_analysis.exporter import export_results

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

ROOT = Path(__file__).resolve().parents[3]
RESULTS_CSV = ROOT / "data" / "process" / "results.csv"


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        content = await file.read()
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


@router.get("/results/export")
async def export_last_results():
    if not RESULTS_CSV.exists():
        raise HTTPException(
            status_code=404,
            detail="No analysis results available. Run POST /api/incidents/analyze first.",
        )
    return FileResponse(
        path=RESULTS_CSV,
        media_type="text/csv",
        filename="results.csv",
    )