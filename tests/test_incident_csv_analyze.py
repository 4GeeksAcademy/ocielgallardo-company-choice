"""CSV structure and size validation for POST /api/incidents/analyze."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "incident-csv-test-secret")

from services.app.models.user import UserPublic, UserRole
from services.app.routers import incidents as incidents_module
from services.incidents_analysis.csv_reader import (
    IncidentCsvError,
    read_incidents,
    read_incidents_from_bytes,
)

REQUIRED_HEADER = (
    "incident_id,date,clinic_id,country,category,description,status,"
    "patient_id,satisfaction_score"
)
VALID_ROW = (
    "HC-000001,2024-01-13,US-TX-02,US,ADMINISTRATIVE,"
    "Patient registration data contains error from onboarding,CLOSED,"
    "PAT-735605,3"
)
PHI_VALUE = "PAT-735605"

_USER = UserPublic(
    id=1,
    email="csv.tester@healthcore.example",
    is_active=True,
    role=UserRole.USER,
    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)


def _csv_bytes(*rows: str) -> bytes:
    return ("\n".join(rows) + "\n").encode("utf-8")


def _post_csv(client: TestClient, content: bytes, filename: str = "incidents.csv"):
    return client.post(
        "/api/incidents/analyze",
        files={"file": (filename, content, "text/csv")},
    )


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "services.app.domain.incident_service.RESULTS_CSV",
        tmp_path / "results.csv",
    )
    application = FastAPI()
    application.include_router(incidents_module.router)
    application.dependency_overrides[incidents_module.get_current_user] = lambda: _USER
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()


def test_valid_csv_returns_summary(client: TestClient) -> None:
    response = _post_csv(client, _csv_bytes(REQUIRED_HEADER, VALID_ROW))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["valid"] == 1
    assert PHI_VALUE not in response.text


def test_satisfaction_score_column_is_optional(client: TestClient) -> None:
    header = "incident_id,date,clinic_id,country,category,description,status,patient_id"
    row = (
        "HC-000002,2024-01-17,UK-LON-02,UK,APPOINTMENT,"
        "Patient not informed of appointment reschedule by clinic,OPEN,PAT-539001"
    )
    response = _post_csv(client, _csv_bytes(header, row))
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_missing_required_columns_returns_400(client: TestClient) -> None:
    header = "incident_id,clinic_id,country,category,description,status,patient_id"
    row = (
        "HC-000001,US-TX-02,US,ADMINISTRATIVE,"
        "Patient registration data contains error from onboarding,CLOSED,PAT-735605"
    )
    response = _post_csv(client, _csv_bytes(header, row))
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "missing required columns" in detail
    assert "date" in detail
    assert PHI_VALUE not in detail
    assert "PAT-" not in detail


def test_missing_several_required_columns_lists_all_of_them(
    client: TestClient,
) -> None:
    header = "incident_id,date,description,status,patient_id"
    row = "HC-000001,2024-01-13,A valid description,OPEN,PAT-735605"
    response = _post_csv(client, _csv_bytes(header, row))
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail == (
        "The CSV is missing required columns: clinic_id, country, category."
    )
    assert "PAT-735605" not in detail


def test_empty_file_returns_400(client: TestClient) -> None:
    response = _post_csv(client, b"")
    assert response.status_code == 400
    assert response.json()["detail"] == "The CSV file is empty."


def test_whitespace_only_file_returns_400(client: TestClient) -> None:
    response = _post_csv(client, b"   \n\n  ")
    assert response.status_code == 400
    assert response.json()["detail"] == "The CSV file is empty."


def test_non_utf8_file_returns_400(client: TestClient) -> None:
    response = _post_csv(client, b"\xff\xfe incident_id,date\n")
    assert response.status_code == 400
    assert response.json()["detail"] == "The CSV file must be UTF-8 encoded."


def test_latin1_file_returns_400(client: TestClient) -> None:
    payload = "incident_id,date,caf\xe9\n".encode("latin-1")
    response = _post_csv(client, payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "The CSV file must be UTF-8 encoded."


def test_no_header_row_returns_400(client: TestClient) -> None:
    response = _post_csv(client, b",,,\n")
    assert response.status_code == 400
    assert response.json()["detail"] == "The CSV file has no header row."


def test_file_over_5mb_returns_413(client: TestClient) -> None:
    oversized = b"x" * (incidents_module.MAX_INCIDENT_CSV_BYTES + 1)
    response = _post_csv(client, oversized)
    assert response.status_code == 413
    assert response.json()["detail"] == "The CSV file exceeds the 5 MB size limit."


def test_file_at_5mb_limit_is_not_rejected_for_size(client: TestClient) -> None:
    header = REQUIRED_HEADER.encode("utf-8") + b"\n"
    padding = incidents_module.MAX_INCIDENT_CSV_BYTES - len(header)
    # Newlines keep fields short; this only asserts the size check allows 5 MB.
    exact = header + (b"\n" * padding)
    assert len(exact) == incidents_module.MAX_INCIDENT_CSV_BYTES
    response = _post_csv(client, exact)
    assert response.status_code != 413
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_unparseable_csv_returns_400(client: TestClient) -> None:
    # A single field larger than csv.field_size_limit must not become a 500,
    # and the message must not echo row contents (PHI).
    huge_field = "PAT-735605" + ("x" * 200_000)
    payload = (REQUIRED_HEADER + "\n" + huge_field + "\n").encode("utf-8")
    response = _post_csv(client, payload)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail == "The CSV file could not be parsed."
    assert "PAT-735605" not in detail
    assert "PAT-735605" not in response.text


def test_non_csv_filename_still_rejected(client: TestClient) -> None:
    response = _post_csv(client, b"not a csv", filename="notes.txt")
    assert response.status_code == 400
    assert response.json()["detail"] == "CSV file required"


def test_read_incidents_raises_for_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "incidents.csv"
    path.write_text(
        "incident_id,date,clinic_id,country,description,status,patient_id\n"
        f"HC-1,2024-01-13,US-TX-02,US,A valid description,OPEN,{PHI_VALUE}\n",
        encoding="utf-8",
    )
    with pytest.raises(IncidentCsvError) as exc_info:
        read_incidents(path)
    message = str(exc_info.value)
    assert "category" in message
    assert PHI_VALUE not in message


def test_read_incidents_from_bytes_rejects_empty() -> None:
    with pytest.raises(IncidentCsvError, match="empty"):
        read_incidents_from_bytes(b"")


def test_header_only_csv_is_accepted(client: TestClient) -> None:
    response = _post_csv(client, _csv_bytes(REQUIRED_HEADER))
    assert response.status_code == 200
    assert response.json()["total"] == 0
