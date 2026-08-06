from datetime import datetime, timezone
from tinydb import Query

from services.app.core.database import users_table, profiles_table
from services.app.core.security import hash_password
from services.app.models.user import UserCreate, UserPublic, UserRole


def create_user(payload: UserCreate) -> UserPublic:
    User = Query()
    if users_table.search(User.email == str(payload.email)):
        raise ValueError("Email already registered")
    user_doc = {
        "email": str(payload.email),
        "hashed_password": hash_password(payload.password),
        "is_active": True,
        "role": payload.role.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    user_id = users_table.insert(user_doc)

    # 3) profile ligado
    profiles_table.insert({
        "user_id": user_id,
        "name": payload.name,
        "phone": payload.phone,
        "address": payload.address,
    })

    stored = users_table.get(doc_id=user_id)
    return UserPublic(
        id=user_id,
        email=stored["email"],
        is_active=stored["is_active"],
        role=UserRole(stored["role"]),
        created_at=stored["created_at"],
    )

class UserNotFoundError(LookupError):
    """Raised when a user id/email does not exist in TinyDB."""


def _doc_to_public(doc) -> UserPublic:
    return UserPublic(
        id=doc.doc_id,
        email=doc["email"],
        is_active=doc["is_active"],
        role=UserRole(doc["role"]),
        created_at=doc["created_at"],
    )


def get_user_by_id(user_id: int) -> UserPublic:
    doc = users_table.get(doc_id=user_id)
    if doc is None:
        raise UserNotFoundError(f"User {user_id} not found")
    return _doc_to_public(doc)


def get_user_by_email(email: str) -> dict | None:
    """Returns the raw TinyDB doc (includes hashed_password) or None.
    Login needs the hash; public endpoints should use UserPublic helpers.
    """
    User = Query()
    rows = users_table.search(User.email == email)
    return rows[0] if rows else None

def list_users() -> list[UserPublic]:
    """Return all users without password hashes."""
    return [_doc_to_public(doc) for doc in users_table.all()]