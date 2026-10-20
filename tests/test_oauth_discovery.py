"""OAuth 2.1 discovery + RS256 service-token tests (hito 25, Fase 1).

Offline: in-memory client registry, no network. Covers the
authorization-server side of the MCP ticket — discovery document, JWKS,
RS256 mint/verify round trip and the fail-closed rules that keep service
identity out of the legacy HS256 path.

The RS256 key comes from ``oauth_keys`` (auto-generated once under the
gitignored ``data/process/auth/`` when no env override is set).
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("SECRET_KEY", "service-identity-test-secret")

import pytest
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jose import JWTError, jwt  # noqa: E402
from jwt import PyJWK  # noqa: E402
from jwt.algorithms import RSAAlgorithm  # noqa: E402
from mcpauth.config import AuthorizationServerMetadata  # noqa: E402
from mcpauth.utils import create_verify_jwt  # noqa: E402
from tinydb import TinyDB  # noqa: E402
from tinydb.storages import MemoryStorage  # noqa: E402

from services.app.core import oauth_keys, security, service_identity  # noqa: E402
from services.app.core.middleware import timing_middleware  # noqa: E402
from services.app.core.security import (  # noqa: E402
    OAUTH_ISSUER_URL,
    SERVICE_ALGORITHM,
    SERVICE_TOKEN_TYPE,
    create_access_token,
    decode_service_claims,
    decode_token_claims,
)
from services.app.routers.auth import router as auth_router  # noqa: E402
from services.app.routers.incidents import router as incidents_router  # noqa: E402
from services.app.routers.oauth import (  # noqa: E402
    SCOPES_SUPPORTED,
    authorization_server_metadata,
    router as oauth_router,
)

CLIENT_ID = "langgraph-agent"
CLIENT_SECRET = "unit-test-secret-not-a-real-one"


def _make_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(timing_middleware)
    app.include_router(auth_router)
    app.include_router(incidents_router)
    app.include_router(oauth_router)
    return app


class _AppFixture:
    """In-memory service registry + mini API (auth + incidents + oauth)."""

    def __init__(self, monkeypatch) -> None:
        memory_db = TinyDB(storage=MemoryStorage)
        monkeypatch.setattr(
            service_identity,
            "service_clients_table",
            memory_db.table("service_clients"),
        )
        self.client = TestClient(_make_app())
        self.register()

    def register(self, scopes=("incidents:read", "inventory:read")) -> None:
        service_identity.register_service_client(CLIENT_ID, CLIENT_SECRET, scopes)

    def grant(self, audience: str | None = None) -> dict:
        body = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
        if audience is not None:
            body["audience"] = audience
        response = self.client.post("/auth/token", json=body)
        assert response.status_code == 200, response.text
        return response.json()

    @property
    def token(self) -> str:
        return self.grant()["access_token"]


@pytest.fixture()
def app(monkeypatch) -> _AppFixture:
    return _AppFixture(monkeypatch)


# --- Discovery document (RFC 8414 / OIDC) ---


def test_openid_configuration_is_parsable_as_as_metadata(app) -> None:
    response = app.client.get("/.well-known/openid-configuration")

    assert response.status_code == 200
    doc = response.json()
    assert doc["issuer"] == OAUTH_ISSUER_URL
    assert doc["token_endpoint"] == f"{OAUTH_ISSUER_URL}/auth/token"
    assert doc["jwks_uri"] == f"{OAUTH_ISSUER_URL}/.well-known/jwks.json"
    assert doc["grant_types_supported"] == ["client_credentials"]
    assert doc["id_token_signing_alg_values_supported"] == ["RS256"]
    assert set(doc["scopes_supported"]) == set(SCOPES_SUPPORTED)

    # Exactly what mcpauth parses when the MCP server starts up.
    metadata = AuthorizationServerMetadata(**doc)
    assert metadata.issuer == OAUTH_ISSUER_URL
    assert metadata.jwks_uri.endswith("/.well-known/jwks.json")


def test_oauth_authorization_server_wellknown_serves_the_same_doc(app) -> None:
    openid = app.client.get("/.well-known/openid-configuration").json()
    oauth = app.client.get("/.well-known/oauth-authorization-server")

    assert oauth.status_code == 200
    assert oauth.json() == openid


def test_authorize_endpoint_is_an_explicit_not_supported_stub(app) -> None:
    response = app.client.get("/auth/authorize")

    assert response.status_code == 501
    body = response.json()
    assert body["error"] == "unsupported_response_type"
    assert "client-credentials" in body["error_description"]


# --- JWKS and RS256 round trip ---


def test_jwks_publishes_public_only_key_matching_minted_token(app) -> None:
    jwks_doc = app.client.get("/.well-known/jwks.json")
    assert jwks_doc.status_code == 200

    key = jwks_doc.json()["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == SERVICE_ALGORITHM
    assert key["use"] == "sig"
    assert "d" not in key and "p" not in key

    header = jwt.get_unverified_header(app.token)
    assert header["alg"] == SERVICE_ALGORITHM
    assert header["kid"] == key["kid"]
    assert header["kid"] == oauth_keys.get_kid()

    public_key = RSAAlgorithm.from_jwk(json.dumps(key))
    claims = jwt.decode(
        app.token,
        public_key,
        algorithms=[SERVICE_ALGORITHM],
        options={"verify_aud": False},
    )
    assert claims["sub"] == f"svc:{CLIENT_ID}"


def test_service_token_claims_carry_iss_aud_and_client_id(app) -> None:
    claims = decode_token_claims(app.token)

    assert claims["iss"] == OAUTH_ISSUER_URL
    assert claims["aud"] == security.OAUTH_DEFAULT_AUDIENCE
    assert claims["typ"] == SERVICE_TOKEN_TYPE
    assert claims["client_id"] == CLIENT_ID
    assert claims["exp"] > claims["iat"]


def test_grant_honours_explicit_audience(app) -> None:
    resource = "http://localhost:8100/mcp"
    token = app.grant(audience=resource)["access_token"]

    claims = decode_token_claims(token)
    assert claims["aud"] == resource


def test_mcpauth_verifier_accepts_our_token_via_jwks(app) -> None:
    """The exact verifier MCP Auth uses: JWKS + iss + scope projection."""
    key = app.client.get("/.well-known/jwks.json").json()["keys"][0]
    verify = create_verify_jwt(PyJWK(key))

    auth_info = verify(app.token)

    assert auth_info.issuer == OAUTH_ISSUER_URL
    assert auth_info.subject == f"svc:{CLIENT_ID}"
    assert auth_info.client_id == CLIENT_ID
    assert auth_info.scopes == ["incidents:read", "inventory:read"]
    assert auth_info.claims["typ"] == SERVICE_TOKEN_TYPE


# --- Fail-closed rules ---


def test_hs256_service_token_is_rejected(app) -> None:
    """Even a correctly signed HS256 typ=service token must not verify."""
    from services.app.core.security import SECRET_KEY

    legacy = jwt.encode(
        {
            "sub": f"svc:{CLIENT_ID}",
            "typ": SERVICE_TOKEN_TYPE,
            "scope": "incidents:read",
            "iss": OAUTH_ISSUER_URL,
            "iat": 1,
            "exp": 9_999_999_999,
        },
        SECRET_KEY,
        algorithm="HS256",
    )

    with pytest.raises(JWTError):
        decode_token_claims(legacy)


def test_token_with_foreign_issuer_is_rejected(app, monkeypatch) -> None:
    token = app.token
    monkeypatch.setattr(security, "OAUTH_ISSUER_URL", "https://other.example")

    with pytest.raises(JWTError):
        decode_service_claims(token)


def test_rs256_token_signed_by_a_foreign_key_is_rejected(app) -> None:
    from cryptography.hazmat.primitives.asymmetric import rsa

    foreign = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = jwt.encode(
        {
            "sub": f"svc:{CLIENT_ID}",
            "typ": SERVICE_TOKEN_TYPE,
            "scope": "incidents:read incidents:write",
            "iss": OAUTH_ISSUER_URL,
            "iat": 1,
            "exp": 9_999_999_999,
        },
        foreign,
        algorithm="RS256",
        headers={"kid": "not-our-kid"},
    )

    with pytest.raises(JWTError):
        decode_service_claims(forged)


def test_human_session_tokens_keep_working_unchanged() -> None:
    claims = decode_token_claims(create_access_token(7))
    assert claims["sub"] == "7"
    assert claims.get("typ") is None


def test_discovery_metadata_helper_is_stable() -> None:
    doc = authorization_server_metadata()
    assert doc == authorization_server_metadata()
    assert doc["authorization_endpoint"].endswith("/auth/authorize")
