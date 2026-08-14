"""
Shared pytest fixtures for AUTH-088.

Why this file exists:
- pytest loads `conftest.py` automatically for every test in this folder.
- Here we set a fake SECRET_KEY and swap TinyDB for a temporary file
  so tests never touch `data/process/auth/auth.json`.
"""

from __future__ import annotations

import os

# Must be set BEFORE importing services.app.core.security (it reads SECRET_KEY at import).
os.environ.setdefault("SECRET_KEY", "pytest-only-secret-key-not-for-production")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("FRONTEND_BASE_URL", "http://localhost:3000")
os.environ.setdefault("RESEND_API_KEY", "re_test_dummy")
os.environ.setdefault("EMAIL_FROM", "onboarding@resend.dev")
os.environ.setdefault("EMAIL_SSL_VERIFY", "false")

import pytest
from tinydb import TinyDB

from services.app.models.user import UserCreate, UserRole
from services.app.domain import user_service


@pytest.fixture
def auth_tables(tmp_path, monkeypatch):
    """
    Isolated TinyDB tables for one test.

    `tmp_path` is a fresh temp folder pytest creates per test.
    `monkeypatch` replaces the table objects that domain modules already imported.
    """
    db_path = tmp_path / "auth-test.json"
    auth_db = TinyDB(db_path)
    users = auth_db.table("users")
    profiles = auth_db.table("profiles")
    reset_tokens = auth_db.table("password_reset_tokens")

    # Patch the database module itself.
    monkeypatch.setattr("services.app.core.database.users_table", users)
    monkeypatch.setattr("services.app.core.database.profiles_table", profiles)
    monkeypatch.setattr(
        "services.app.core.database.password_reset_tokens_table", reset_tokens
    )

    # Patch every domain module that did `from ...database import users_table`.
    # Without this, tests would still write to the real auth.json.
    monkeypatch.setattr("services.app.domain.user_service.users_table", users)
    monkeypatch.setattr("services.app.domain.user_service.profiles_table", profiles)
    monkeypatch.setattr("services.app.domain.profile_service.profiles_table", profiles)
    monkeypatch.setattr("services.app.domain.password_reset_service.users_table", users)
    monkeypatch.setattr(
        "services.app.domain.password_reset_service.password_reset_tokens_table",
        reset_tokens,
    )

    yield {
        "users": users,
        "profiles": profiles,
        "reset_tokens": reset_tokens,
        "db_path": db_path,
    }

    auth_db.close()


@pytest.fixture
def sample_user(auth_tables):
    """
    Creates one active user in the isolated DB and returns UserPublic.
    Depends on `auth_tables` so the temp DB is already patched.
    """
    return user_service.create_user(
        UserCreate(
            email="tester@example.com",
            password="password123",
            role=UserRole.USER,
            name="Test User",
        )
    )