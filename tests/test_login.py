"""Unit tests for authenticate_user (login business logic)."""

import pytest

from services.app.core.security import decode_access_token
from services.app.domain.user_service import (
    authenticate_user,
    InvalidCredentialsError,
)


def test_authenticate_user_happy_path(sample_user):
    """Happy: correct credentials return a JWT whose sub is the user id."""
    token = authenticate_user(str(sample_user.email), "password123")

    assert isinstance(token, str)
    assert decode_access_token(token) == str(sample_user.id)


def test_authenticate_user_edge_inactive_account(auth_tables, sample_user):
    """Edge: inactive user must not receive a token."""
    auth_tables["users"].update({"is_active": False}, doc_ids=[sample_user.id])

    with pytest.raises(InvalidCredentialsError):
        authenticate_user(str(sample_user.email), "password123")


def test_authenticate_user_fails_wrong_password(sample_user):
    """Fail: wrong password raises InvalidCredentialsError."""
    with pytest.raises(InvalidCredentialsError):
        authenticate_user(str(sample_user.email), "not-the-password")


def test_authenticate_user_fails_unknown_email(auth_tables):
    """Fail: unknown email raises the same InvalidCredentialsError (no leak)."""
    with pytest.raises(InvalidCredentialsError):
        authenticate_user("nobody@example.com", "password123")