"""Unit tests for user registration (create_user business logic)."""

import pytest
from pydantic import ValidationError

from services.app.domain import user_service
from services.app.domain.user_service import create_user
from services.app.models.user import UserCreate, UserRole
from services.app.core.security import verify_password


def test_create_user_happy_path(auth_tables):
    """Happy: valid payload creates user + profile; password is hashed."""
    user = create_user(
        UserCreate(
            email="new.user@example.com",
            password="password123",
            role=UserRole.USER,
            name="New User",
        )
    )

    assert user.email == "new.user@example.com"
    assert user.role == UserRole.USER
    assert user.is_active is True

    # Password must be stored hashed, never plain text
    raw = auth_tables["users"].get(doc_id=user.id)
    assert raw is not None
    assert raw["hashed_password"] != "password123"
    assert verify_password("password123", raw["hashed_password"]) is True

    # Profile row linked to the same user id
    profiles = auth_tables["profiles"].all()
    assert any(p["user_id"] == user.id for p in profiles)


def test_create_user_edge_password_exactly_8_chars(auth_tables):
    """Edge: password length exactly 8 (minimum allowed by the model)."""
    user = create_user(
        UserCreate(
            email="edge8@example.com",
            password="12345678",  # exactly 8
            role=UserRole.USER,
        )
    )
    assert user.id is not None


def test_create_user_fails_on_duplicate_email(auth_tables, sample_user):
    """Fail: registering the same email twice raises ValueError."""
    with pytest.raises(ValueError, match="Email already registered"):
        create_user(
            UserCreate(
                email=sample_user.email,  # already created by fixture
                password="password123",
                role=UserRole.USER,
            )
        )


def test_create_user_fails_on_short_password(auth_tables):
    """Fail: password shorter than 8 is rejected by the Pydantic model."""
    with pytest.raises(ValidationError):
        UserCreate(
            email="short@example.com",
            password="1234567",  # 7 chars — too short
            role=UserRole.USER,
        )