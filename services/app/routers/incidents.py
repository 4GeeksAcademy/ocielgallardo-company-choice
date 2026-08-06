from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

from services.app.domain.incident_service import analyze_csv_bytes, results_csv_path

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")

    content = await file.read()
    return analyze_csv_bytes(content)


@router.get("/results/export")
async def export_last_results():
    results_csv = results_csv_path()
    if not results_csv.exists():
        raise HTTPException(
            status_code=404,
            detail="No analysis results available. Run POST /api/incidents/analyze first.",
        )
    return FileResponse(
        path=results_csv,
        media_type="text/csv",
        filename="results.csv",
    )
