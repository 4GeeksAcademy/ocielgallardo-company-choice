from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from services.app.core.security import decode_access_token
from services.app.domain.user_service import get_user_by_id, UserNotFoundError
from services.app.models.user import UserPublic, UserRole

# Le dice a /docs dónde está el login (para el botón Authorize)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = int(decode_access_token(token))
    except (JWTError, ValueError):
        raise credentials_exception

    try:
        return get_user_by_id(user_id)
    except UserNotFoundError:
        raise credentials_exception


def require_self_or_admin(current_user: UserPublic, user_id: int) -> None:
    """Raise 403 unless the caller is the target user or an admin."""
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )