"""Backend tests for the service-identity client-credentials flow (§9.1).

Offline: the service-identity registry is swapped for an in-memory TinyDB
table and the human user lookup is stubbed — no Supabase/network required.
Covers the acceptance criteria of ``docs/rag/agent-graph.md`` §9.1 at the
HTTP layer (grant, principal, scope, fail-closed, revocation, audit log).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("SECRET_KEY", "service-identity-test-secret")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402
from tinydb import TinyDB  # noqa: E402
from tinydb.storages import MemoryStorage  # noqa: E402

from services.app.core import deps, service_identity  # noqa: E402
from services.app.core.middleware import timing_middleware  # noqa: E402
from services.app.core.security import (  # noqa: E402
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    decode_token_claims,
)
from services.app.domain.user_service import UserNotFoundError  # noqa: E402
from services.app.models.user import UserPublic, UserRole  # noqa: E402
from services.app.routers import incidents as incidents_module  # noqa: E402
from services.app.routers.auth import router as auth_router  # noqa: E402
from services.app.routers.incidents import router as incidents_router  # noqa: E402

CLIENT_ID = "langgraph-agent"
CLIENT_SECRET = "unit-test-secret-not-a-real-one"

_VALID_INCIDENT_WRITE = {
    "title": "Service identity write attempt",
    "description": "Requires the incidents:write scope for service principals",
    "category": "it_system",
    "origin": "internal",
    "branch": "central",
}

_HUMAN = UserPublic(
    id=11,
    email="qa.human@healthcore.example",
    is_active=True,
    role=UserRole.USER,
    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)


def _fake_user_getter(user_id: int) -> UserPublic:
    if user_id == _HUMAN.id:
        return _HUMAN
    raise UserNotFoundError(f"User {user_id} not found")


class _FakeRequest:
    """Minimal stand-in for FastAPI's Request (state only)."""

    def __init__(self) -> None:
        self.state = type("State", (), {})()


def _make_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(timing_middleware)
    app.include_router(auth_router)
    app.include_router(incidents_router)
    return app


class _AppFixture:
    """Shared setup: in-memory client registry + stubbed human users."""

    def __init__(self, monkeypatch) -> None:
        memory_db = TinyDB(storage=MemoryStorage)
        monkeypatch.setattr(
            service_identity,
            "service_clients_table",
            memory_db.table("service_clients"),
        )
        monkeypatch.setattr(deps, "get_user_by_id", _fake_user_getter)
        self.client = TestClient(_make_app())

    def register(self, scopes=("incidents:read", "inventory:read")) -> None:
        service_identity.register_service_client(CLIENT_ID, CLIENT_SECRET, scopes)

    def grant(self) -> dict:
        response = self.client.post(
            "/auth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
        assert response.status_code == 200, response.text
        return response.json()

    @staticmethod
    def bearer(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    @property
    def service_headers(self) -> dict[str, str]:
        return self.bearer(self.grant()["access_token"])

    @property
    def human_headers(self) -> dict[str, str]:
        return self.bearer(create_access_token(_HUMAN.id))


def _app(monkeypatch) -> _AppFixture:
    return _AppFixture(monkeypatch)


# --- Grant endpoint (client-credentials) ---


def test_grant_issues_service_token_with_scopes_and_ttl(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()

    body = fixture.grant()

    assert body["token_type"] == "bearer"
    assert body["expires_in"] == service_identity.SERVICE_TOKEN_EXPIRE_MINUTES * 60
    assert set(body["scope"].split()) == set(service_identity.DEFAULT_SERVICE_SCOPES)

    claims = decode_token_claims(body["access_token"])
    assert claims["typ"] == "service"
    assert claims["sub"] == f"svc:{CLIENT_ID}"
    assert set(claims["scope"].split()) == set(service_identity.DEFAULT_SERVICE_SCOPES)
    assert claims["exp"] > claims["iat"]


def test_grant_rejects_unknown_client_and_wrong_secret_with_same_401(
    monkeypatch,
) -> None:
    fixture = _app(monkeypatch)
    fixture.register()

    unknown = fixture.client.post(
        "/auth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": "nope",
            "client_secret": CLIENT_SECRET,
        },
    )
    wrong_secret = fixture.client.post(
        "/auth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": "wrong",
        },
    )

    assert unknown.status_code == 401
    assert wrong_secret.status_code == 401
    assert unknown.json() == wrong_secret.json()


def test_grant_rejects_non_client_credentials_grant_type(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()

    response = fixture.client.post(
        "/auth/token",
        json={
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )

    # Bare test app (no repo-wide 400 validation handler): Pydantic rejects
    # the Literal grant_type; the deployed app maps it to 400.
    assert response.status_code in (400, 422)


def test_grant_does_not_leak_secret_or_persist_plaintext(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()

    body = fixture.grant()
    assert CLIENT_SECRET not in body["access_token"]

    stored = service_identity.get_service_client(CLIENT_ID)
    assert stored is not None
    assert CLIENT_SECRET not in str(stored)
    assert stored["secret_hash"] != CLIENT_SECRET


# --- Principal verification (human vs service) ---


def test_human_token_is_not_a_service_principal() -> None:
    claims = decode_token_claims(create_access_token(_HUMAN.id))
    assert service_identity.is_service_claims(claims) is False


def test_service_token_authorized_on_scoped_incident_routes(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()
    headers = fixture.service_headers

    listing = fixture.client.get("/api/incidents", headers=headers)
    detail = fixture.client.get("/api/incidents/1", headers=headers)

    assert listing.status_code == 200
    assert detail.status_code in (200, 404)


def test_service_token_rejected_on_unscoped_routes(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()
    headers = fixture.service_headers

    summary = fixture.client.get("/api/incidents/summary", headers=headers)
    auth_me = fixture.client.get("/auth/me", headers=headers)

    assert summary.status_code == 401
    assert auth_me.status_code == 401


def test_service_token_without_write_scope_is_403_on_create(monkeypatch) -> None:
    """Default read-only scopes cannot create incidents (403, not 401)."""
    fixture = _app(monkeypatch)
    fixture.register()

    response = fixture.client.post(
        "/api/incidents",
        json=_VALID_INCIDENT_WRITE,
        headers=fixture.service_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient scope"


def test_service_token_with_write_scope_creates_incident(monkeypatch) -> None:
    """A service principal granted incidents:write may create tickets (MCP server)."""
    fixture = _app(monkeypatch)
    fixture.register(
        scopes=("incidents:read", "incidents:write", "inventory:read")
    )

    created: dict = {}

    def _stub_create(payload):
        created.update(payload.model_dump())
        return incidents_module.Incident(id=4242, created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z", **payload.model_dump())

    monkeypatch.setattr(incidents_module, "create_incident", _stub_create)

    response = fixture.client.post(
        "/api/incidents",
        json=_VALID_INCIDENT_WRITE,
        headers=fixture.service_headers,
    )

    assert response.status_code == 201
    assert created["title"] == _VALID_INCIDENT_WRITE["title"]


def test_service_token_with_write_scope_updates_status(monkeypatch) -> None:
    """PATCH status also requires incidents:write and accepts it when granted."""
    fixture = _app(monkeypatch)
    fixture.register(
        scopes=("incidents:read", "incidents:write", "inventory:read")
    )

    def _stub_update(incident_id: int, payload):
        return incidents_module.Incident(
            id=incident_id,
            title="t",
            description="d",
            category="it_system",
            status=payload.status.value if hasattr(payload.status, "value") else payload.status,
            origin="internal",
            branch="central",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )

    monkeypatch.setattr(incidents_module, "update_incident_status", _stub_update)

    response = fixture.client.patch(
        "/api/incidents/4242/status",
        json={"status": "in_progress"},
        headers=fixture.service_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_human_only_dependency_still_rejects_service_tokens(monkeypatch) -> None:
    """Inventory/user write routes use get_current_user: service tokens stay 401.

    The write scope added for incidents does not leak anywhere else — every
    route that still depends on ``get_current_user`` (e.g. all inventory
    writes) keeps rejecting ``typ=service`` tokens fail-closed.
    """
    fixture = _app(monkeypatch)
    fixture.register(scopes=("incidents:read", "incidents:write", "inventory:read"))

    claims = decode_token_claims(fixture.grant()["access_token"])
    assert service_identity.is_service_claims(claims) is True

    with pytest.raises(Exception) as excinfo:
        deps.get_current_user(
            request=_FakeRequest(),
            token=fixture.grant()["access_token"],
        )
    assert getattr(excinfo.value, "status_code", None) == 401

    # Same human-only dependency guards /api/incidents/summary today.
    summary = fixture.client.get(
        "/api/incidents/summary", headers=fixture.service_headers
    )
    assert summary.status_code == 401


def test_missing_scope_is_403_not_401(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register(scopes=("inventory:read",))

    response = fixture.client.get("/api/incidents", headers=fixture.service_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient scope"


def test_missing_token_is_401(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    assert fixture.client.get("/api/incidents").status_code == 401


def test_human_user_access_is_unchanged(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()
    headers = fixture.human_headers

    listing = fixture.client.get("/api/incidents", headers=headers)
    summary = fixture.client.get("/api/incidents/summary", headers=headers)

    assert listing.status_code == 200
    assert summary.status_code == 200


def test_revoked_client_invalidates_minted_tokens_before_ttl(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()
    headers = fixture.service_headers
    assert fixture.client.get("/api/incidents", headers=headers).status_code == 200

    service_identity.unregister_service_client(CLIENT_ID)

    assert fixture.client.get("/api/incidents", headers=headers).status_code == 401


def test_expired_service_token_is_rejected(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()
    monkeypatch.setattr(service_identity, "SERVICE_TOKEN_EXPIRE_MINUTES", -1)
    headers = fixture.service_headers

    response = fixture.client.get("/api/incidents", headers=headers)
    assert response.status_code == 401


def test_forged_service_claims_without_signature_are_rejected(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()

    forged = jwt.encode(
        {
            "sub": f"svc:{CLIENT_ID}",
            "typ": "service",
            "scope": "incidents:read",
            "exp": datetime.now(timezone.utc).timestamp() + 600,
        },
        "wrong-secret-key",
        algorithm=ALGORITHM,
    )

    response = fixture.client.get("/api/incidents", headers=fixture.bearer(forged))
    assert response.status_code == 401


def test_service_token_with_blank_scope_cannot_read(monkeypatch) -> None:
    fixture = _app(monkeypatch)
    fixture.register()

    blank_scope = service_identity.create_service_token(CLIENT_ID, ())

    response = fixture.client.get("/api/incidents", headers=fixture.bearer(blank_scope))
    assert response.status_code == 403


# --- Audit attribution (api.timing log line) ---


def test_api_log_attributes_service_principal(monkeypatch, caplog) -> None:
    fixture = _app(monkeypatch)
    fixture.register()

    with caplog.at_level(logging.INFO, logger="api.timing"):
        fixture.client.get("/api/incidents", headers=fixture.service_headers)

    assert "principal=svc:langgraph-agent" in caplog.text


def test_api_log_attributes_human_principal(monkeypatch, caplog) -> None:
    fixture = _app(monkeypatch)

    with caplog.at_level(logging.INFO, logger="api.timing"):
        fixture.client.get("/api/incidents/summary", headers=fixture.human_headers)

    assert "principal=user:11" in caplog.text


def test_api_log_marks_unauthenticated_requests(monkeypatch, caplog) -> None:
    fixture = _app(monkeypatch)

    with caplog.at_level(logging.INFO, logger="api.timing"):
        fixture.client.get("/api/incidents")

    assert "principal=-" in caplog.text


def test_secret_key_is_available_for_jwt_ops() -> None:
    assert SECRET_KEY
