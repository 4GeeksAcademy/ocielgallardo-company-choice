import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

from services.app.core import oauth_keys

# Carga el .env de la raíz del monorepo
load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in the environment")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# --- OAuth 2.1 / OIDC (service tokens) -------------------------------------
# Human sessions keep HS256+SECRET_KEY; service tokens are RS256 signed by
# oauth_keys so resource servers (MCP server via mcpauth) verify them from
# /.well-known/jwks.json without sharing a symmetric secret.
SERVICE_ALGORITHM = "RS256"
SERVICE_TOKEN_TYPE = "service"
OAUTH_ISSUER_URL = (os.getenv("OAUTH_ISSUER_URL") or "http://localhost:8000").rstrip(
    "/"
)
OAUTH_DEFAULT_AUDIENCE = (
    os.getenv("OAUTH_TOKEN_AUDIENCE") or OAUTH_ISSUER_URL
).rstrip("/")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str | int) -> str:
    """Create a signed JWT. `subject` = TinyDB user id."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),  # id del usuario (siempre string en JWT)
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token_claims(token: str) -> dict:
    """Decode and validate either token flavour; raise JWTError if invalid.

    Dispatches on the JWT ``alg`` header: RS256 goes through the OAuth
    service path (JWKS + ``iss``), everything else through the human
    HS256 path. HS256-signed ``typ=service`` tokens are rejected so the
    legacy symmetric secret can never mint service identity again.
    """
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except JWTError:
        raise
    if alg == SERVICE_ALGORITHM:
        return decode_service_claims(token)
    claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if claims.get("typ") == SERVICE_TOKEN_TYPE:
        raise JWTError("service tokens must be signed with RS256 (OAUTH_ISSUER_URL)")
    return claims


def decode_service_claims(token: str) -> dict:
    """Decode an RS256 service token against the OAuth JWKS and issuer.

    Signature, ``exp``, ``iat`` and ``iss`` are enforced here; ``aud`` is
    *not* (several audiences are valid: the API for backend calls, the MCP
    resource for agents) — audience is a resource-server concern and is
    checked there by MCP Auth when configured.
    """
    claims = jwt.decode(
        token,
        oauth_keys.get_public_pem(),
        algorithms=[SERVICE_ALGORITHM],
        issuer=OAUTH_ISSUER_URL,
        options={
            "require": ["exp", "iat", "sub", "iss", "typ"],
            "verify_aud": False,
        },
    )
    if claims.get("typ") != SERVICE_TOKEN_TYPE:
        raise JWTError("RS256 token is not a service token")
    return claims


def decode_access_token(token: str) -> str:
    """Return the user id (sub) or raise JWTError if invalid/expired."""
    payload = decode_token_claims(token)
    subject = payload.get("sub")
    if subject is None:
        raise JWTError("Token missing subject")
    return str(subject)