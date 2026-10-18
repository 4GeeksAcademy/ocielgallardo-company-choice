"""RS256 signing material for OAuth service tokens (AS side of the API).

The API acts as its own OAuth 2.1 / OIDC authorization server for the MCP
ecosystem: service tokens are signed RS256 with a dedicated key pair and the
public half is published as a JWKS, so resource servers (the MCP server via
``mcpauth``) verify them without sharing a symmetric secret.

Key material is never committed (``data/process/auth/*.pem`` is gitignored).
Resolution order:

1. ``OAUTH_JWT_PRIVATE_KEY_PEM`` — raw PEM inline (containers/secrets),
2. ``OAUTH_JWT_PRIVATE_KEY_FILE`` — path to an existing PEM file,
3. otherwise a fresh 2048-bit key is generated once and persisted at
   ``data/process/auth/oauth_service_signing_key.pem`` (mode 0600), matching
   how the runtime TinyDB stores already live under ``data/process/``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import load_dotenv

load_dotenv()

DEFAULT_KEY_PATH = Path("data/process/auth/oauth_service_signing_key.pem")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _int_to_b64url(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    return _b64url(value.to_bytes(length, "big"))


@lru_cache(maxsize=1)
def _signing_key() -> rsa.RSAPrivateKey:
    inline = (os.getenv("OAUTH_JWT_PRIVATE_KEY_PEM") or "").strip()
    if inline:
        return serialization.load_pem_private_key(inline.encode(), password=None)

    path = Path(os.getenv("OAUTH_JWT_PRIVATE_KEY_FILE") or DEFAULT_KEY_PATH)
    if path.is_file():
        return serialization.load_pem_private_key(path.read_bytes(), password=None)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    try:
        os.chmod(path, 0o600)
    except OSError:  # pragma: no cover - platform-dependent
        pass
    return key


def _public_numbers() -> rsa.RSAPublicNumbers:
    return _signing_key().public_key().public_numbers()


@lru_cache(maxsize=1)
def get_kid() -> str:
    """RFC 7638 thumbprint of the public key (stable key id for JWKS/JWT)."""
    numbers = _public_numbers()
    jwk = json.dumps(
        {
            "e": _int_to_b64url(numbers.e),
            "kty": "RSA",
            "n": _int_to_b64url(numbers.n),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return _b64url(hashlib.sha256(jwk.encode("ascii")).digest())


def get_public_jwks() -> dict:
    """JWKS document served at ``/.well-known/jwks.json``."""
    numbers = _public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": get_kid(),
                "n": _int_to_b64url(numbers.n),
                "e": _int_to_b64url(numbers.e),
            }
        ]
    }


def get_signing_pem() -> str:
    """Private key PEM used to sign service tokens (RS256)."""
    return _signing_key().private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def get_public_pem() -> str:
    """Public key PEM used to verify service tokens inside the API."""
    return _signing_key().public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def clear_caches() -> None:
    """Test hook: forget cached key material (env changes take effect)."""
    _signing_key.cache_clear()
    get_kid.cache_clear()


__all__ = [
    "DEFAULT_KEY_PATH",
    "clear_caches",
    "get_kid",
    "get_public_jwks",
    "get_public_pem",
    "get_signing_pem",
]
