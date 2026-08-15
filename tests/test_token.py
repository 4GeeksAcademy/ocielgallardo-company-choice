"""Unit tests for get_current_user and /auth/me business decisions."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from services.app.core import security
from services.app.core.deps import get_current_user
from services.app.core.security import create_access_token
from services.app.domain.profile_service import (
    get_profile_by_user_id,
    ProfileNotFoundError,
)
from services.app.domain.user_service import delete_user


def _me_payload(current_user):
    """
    Same decision as routers.auth.read_me — profile or None.
    Kept here so we assert business logic, not FastAPI wiring.
    """
    try:
        profile = get_profile_by_user_id(current_user.id)
    except ProfileNotFoundError:
        profile = None
    return {
        "email": current_user.email,
        "role": current_user.role,
        "profile": profile,
    }


def test_get_current_user_happy_path(sample_user):
    """Happy: valid JWT resolves to the matching UserPublic."""
    token = create_access_token(sample_user.id)

    user = get_current_user(token=token)

    assert user.id == sample_user.id
    assert user.email == sample_user.email


def test_me_edge_user_without_profile(auth_tables, sample_user):
    """Edge: user exists but profile row is gone → profile is None."""
    # Remove profile rows for this user (user account stays)
    auth_tables["profiles"].truncate()

    token = create_access_token(sample_user.id)
    current = get_current_user(token=token)
    payload = _me_payload(current)

    assert payload["email"] == sample_user.email
    assert payload["profile"] is None


def test_get_current_user_fails_invalid_token(auth_tables):
    """Fail: garbage token → 401 credentials exception."""
    with pytest.raises(HTTPException) as exc:
        get_current_user(token="not-a-jwt")
    assert exc.value.status_code == 401


def test_get_current_user_fails_expired_token(sample_user):
    """Fail: expired JWT → 401."""
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": str(sample_user.id), "exp": expire},
        security.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token)
    assert exc.value.status_code == 401


def test_get_current_user_fails_deleted_user(auth_tables, sample_user):
    """Fail: token for a user id that no longer exists → 401."""
    token = create_access_token(sample_user.id)
    delete_user(sample_user.id)

    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token)
    assert exc.value.status_code == 401