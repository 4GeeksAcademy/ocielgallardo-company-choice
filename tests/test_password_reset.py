"""Unit tests for forgot / reset / change password (domain logic only)."""

from datetime import datetime, timedelta, timezone
import hashlib

import pytest
from fastapi import HTTPException

from services.app.core.security import verify_password
from services.app.domain import password_reset_service as prs


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- forgot_password ---------------------------------------------------

def test_forgot_password_happy_path_creates_token(auth_tables, sample_user, monkeypatch):
    """Happy: known email creates a reset token; email send is mocked."""
    monkeypatch.setattr(prs, "_send_password_reset_email", lambda **kwargs: None)

    result = prs.forgot_password(str(sample_user.email))

    assert result == {"message": "ok"}
    assert len(auth_tables["reset_tokens"].all()) == 1


def test_forgot_password_edge_unknown_email_same_response(auth_tables):
    """Edge: unknown email still returns ok (no user enumeration)."""
    result = prs.forgot_password("nobody@example.com")

    assert result == {"message": "ok"}
    assert auth_tables["reset_tokens"].all() == []


def test_forgot_password_fail_email_error_still_ok(auth_tables, sample_user, monkeypatch):
    """Fail mode for client: provider error still returns ok (no leak)."""

    def boom(**kwargs):
        raise HTTPException(status_code=500, detail="Unable to send email.")

    monkeypatch.setattr(prs, "_send_password_reset_email", boom)

    result = prs.forgot_password(str(sample_user.email))

    assert result == {"message": "ok"}


# --- reset_password ----------------------------------------------------

def test_reset_password_happy_path(auth_tables, sample_user):
    """Happy: valid token updates hash and deletes the token (single-use)."""
    plain_token = prs.create_password_reset_token(sample_user.id)

    result = prs.reset_password(token=plain_token, new_password="newpass123")

    assert result == {"message": "ok"}
    raw = auth_tables["users"].get(doc_id=sample_user.id)
    assert verify_password("newpass123", raw["hashed_password"]) is True
    assert auth_tables["reset_tokens"].all() == []  # consumed


def test_reset_password_edge_new_token_invalidates_old(auth_tables, sample_user):
    """Edge: creating a second token for the same user removes the first."""
    first = prs.create_password_reset_token(sample_user.id)
    second = prs.create_password_reset_token(sample_user.id)

    assert len(auth_tables["reset_tokens"].all()) == 1

    with pytest.raises(HTTPException) as exc_first:
        prs.reset_password(token=first, new_password="newpass123")
    assert exc_first.value.status_code == 400

    # Second token still works
    assert prs.reset_password(token=second, new_password="newpass123") == {"message": "ok"}


def test_reset_password_fails_expired_token(auth_tables, sample_user):
    """Fail: expired token is rejected with 400."""
    plain = "expired-token-value"
    auth_tables["reset_tokens"].insert(
        {
            "user_id": sample_user.id,
            "token_hash": _sha256(plain),
            "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    with pytest.raises(HTTPException) as exc:
        prs.reset_password(token=plain, new_password="newpass123")
    assert exc.value.status_code == 400


def test_reset_password_fails_corrupt_expires_at(auth_tables, sample_user):
    """
    Fail (AI-suggested): corrupt expires_at must be 400, not an unhandled crash.
    """
    plain = "corrupt-expiry-token"
    auth_tables["reset_tokens"].insert(
        {
            "user_id": sample_user.id,
            "token_hash": _sha256(plain),
            "expires_at": "not-a-valid-datetime",
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    with pytest.raises(HTTPException) as exc:
        prs.reset_password(token=plain, new_password="newpass123")
    assert exc.value.status_code == 400
    assert "Invalid or expired" in exc.value.detail


# --- change_password ---------------------------------------------------

def test_change_password_happy_path(auth_tables, sample_user):
    """Happy: correct current password stores a new hash."""
    result = prs.change_password(
        user_id=sample_user.id,
        current_password="password123",
        new_password="changed456",
    )

    assert result == {"message": "ok"}
    raw = auth_tables["users"].get(doc_id=sample_user.id)
    assert verify_password("changed456", raw["hashed_password"]) is True


def test_change_password_edge_new_password_exactly_8(auth_tables, sample_user):
    """Edge: new password length exactly 8 is accepted by domain call."""
    result = prs.change_password(
        user_id=sample_user.id,
        current_password="password123",
        new_password="12345678",
    )
    assert result == {"message": "ok"}


def test_change_password_fails_wrong_current(auth_tables, sample_user):
    """Fail: wrong current password → 400."""
    with pytest.raises(HTTPException) as exc:
        prs.change_password(
            user_id=sample_user.id,
            current_password="wrong-password",
            new_password="changed456",
        )
    assert exc.value.status_code == 400
    assert "Current password" in exc.value.detail