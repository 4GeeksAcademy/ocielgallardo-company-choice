"""Unit tests for password hashing and JWT helpers (business logic only)."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import JWTError, jwt

from services.app.core import security


# --- Password hashing -------------------------------------------------

def test_hash_and_verify_password_happy_path():
    """Happy: a hashed password verifies against the original plain text."""
    hashed = security.hash_password("password123")

    assert hashed != "password123"  # never store plain text
    assert security.verify_password("password123", hashed) is True


def test_verify_password_fails_with_wrong_password():
    """Fail: wrong plain text must not verify."""
    hashed = security.hash_password("password123")

    assert security.verify_password("wrong-password", hashed) is False


# --- JWT create / decode ----------------------------------------------

def test_create_and_decode_access_token_happy_path():
    """Happy: encode then decode returns the same subject (user id)."""
    token = security.create_access_token(42)

    assert isinstance(token, str)
    assert token.count(".") == 2  # JWT has three base64 parts

    subject = security.decode_access_token(token)
    assert subject == "42"  # JWT `sub` is always a string


def test_decode_access_token_rejects_expired_token(monkeypatch):
    """
    Edge / regression: an already-expired token must raise JWTError.

    We build the token ourselves with exp in the past (no real waiting).
    """
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": "7", "exp": expire}
    expired_token = jwt.encode(
        payload,
        security.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )

    with pytest.raises(JWTError):
        security.decode_access_token(expired_token)


def test_decode_access_token_rejects_malformed_token():
    """Fail: garbage string is not a valid JWT."""
    with pytest.raises(JWTError):
        security.decode_access_token("not.a.valid.jwt")


def test_decode_access_token_rejects_token_without_subject():
    """Fail: valid signature but missing `sub` must raise JWTError."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"exp": expire}  # deliberately no "sub"
    token = jwt.encode(
        payload,
        security.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )

    with pytest.raises(JWTError):
        security.decode_access_token(token)