"""A01 regression: auth on previously open surfaces + registration gate."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-not-for-prod")

from services.app.models.user import UserPublic, UserRole  # noqa: E402
from services.app.routers import incidents as incidents_module  # noqa: E402
from services.app.routers import telemetry as telemetry_module  # noqa: E402
from services.app.routers import users as users_module  # noqa: E402
from data.pipelines.rfp_intake.departments import (  # noqa: E402
    user_may_approve_department,
)


def _user(role: UserRole = UserRole.USER, email: str = "user@healthcore.example") -> UserPublic:
    return UserPublic(
        id=1,
        email=email,
        role=role,
        is_active=True,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def incidents_client(monkeypatch):
    application = FastAPI()
    application.include_router(incidents_module.router)
    with TestClient(application) as client:
        yield client


def test_incidents_analyze_requires_auth(incidents_client: TestClient) -> None:
    response = incidents_client.post("/api/incidents/analyze")
    assert response.status_code in {401, 403, 422}


def test_incidents_export_requires_auth(incidents_client: TestClient) -> None:
    response = incidents_client.get("/api/incidents/results/export")
    assert response.status_code == 401


@pytest.fixture
def telemetry_client():
    application = FastAPI()
    application.include_router(telemetry_module.router)

    def _fake_db():
        yield MagicMock()

    application.dependency_overrides[telemetry_module.get_telemetry_db] = _fake_db
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def test_telemetry_report_requires_auth(telemetry_client: TestClient) -> None:
    response = telemetry_client.get("/telemetry/report")
    assert response.status_code == 401


def test_telemetry_ingest_rejects_bad_key(telemetry_client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("TELEMETRY_INGEST_KEY", "expected-key")
    response = telemetry_client.post(
        "/telemetry/events",
        json={"events": []},
        headers={"X-Telemetry-Ingest-Key": "wrong"},
    )
    assert response.status_code == 401


def test_registration_disabled_returns_403(monkeypatch) -> None:
    monkeypatch.setenv("ALLOW_PUBLIC_REGISTRATION", "false")
    application = FastAPI()
    application.include_router(users_module.router)
    with TestClient(application) as client:
        response = client.post(
            "/users",
            json={
                "email": "new@healthcore.example",
                "password": "password123",
            },
        )
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


def test_department_approval_requires_owner_or_admin(monkeypatch) -> None:
    monkeypatch.setenv("RFP_COMPLIANCE_OWNER_EMAIL", "claire@healthcore.example")
    admin = _user(UserRole.ADMIN, "admin@healthcore.example")
    owner = _user(UserRole.MANAGER, "claire@healthcore.example")
    other = _user(UserRole.MANAGER, "other@healthcore.example")
    assert user_may_approve_department(admin, "compliance") is True
    assert user_may_approve_department(owner, "compliance") is True
    assert user_may_approve_department(other, "compliance") is False
