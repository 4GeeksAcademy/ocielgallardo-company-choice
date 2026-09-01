from enum import Enum
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from services.app.models.profile import ProfilePublic


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class UserCreate(BaseModel):
    """Public registration payload. Role is never accepted from the client."""

    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    role: UserRole | None = None
    is_active: bool | None = None


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    role: UserRole
    created_at: datetime


class RegisterResponse(BaseModel):
    """Safe registration confirmation — no email or credentials in the body."""

    id: int
    is_active: bool
    role: UserRole
    created_at: datetime


class LoginRequest(BaseModel):
    username: EmailStr
    password: str
    grant_type: str = "password"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthMeResponse(BaseModel):
    """Safe session projection for GET /auth/me."""

    email: EmailStr
    role: UserRole
    profile: ProfilePublic | None = None


class MessageResponse(BaseModel):
    """Generic confirmation body (password flows)."""

    message: str


class DetailResponse(BaseModel):
    """Generic confirmation body (deletes)."""

    detail: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)