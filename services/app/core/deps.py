from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from services.app.core.security import decode_token_claims
from services.app.core.service_identity import (
    ServicePrincipal,
    ServiceTokenError,
    is_service_claims,
    service_principal_from_claims,
)
from services.app.domain.user_service import get_user_by_id, UserNotFoundError
from services.app.models.user import UserPublic, UserRole

# Le dice a /docs dónde está el login (para el botón Authorize)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> UserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = decode_token_claims(token)
        if is_service_claims(claims):
            # Fail closed: service tokens are only accepted by the scoped
            # read-only tool routes (get_reader_principal / require_scope).
            raise credentials_exception
        user_id = int(claims.get("sub") or "")
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    try:
        user = get_user_by_id(user_id)
    except UserNotFoundError:
        raise credentials_exception

    # Audit attribution: human principal in the api.timing log line.
    request.state.principal = f"user:{user.id}"
    return user


def get_reader_principal(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> UserPublic | ServicePrincipal:
    """Authenticated reader for tool routes: human user or service principal."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = decode_token_claims(token)
    except JWTError:
        raise credentials_exception

    if is_service_claims(claims):
        try:
            principal = service_principal_from_claims(claims)
        except ServiceTokenError:
            raise credentials_exception
        request.state.principal = principal.name
        return principal

    try:
        user_id = int(claims.get("sub") or "")
    except (TypeError, ValueError):
        raise credentials_exception
    try:
        user = get_user_by_id(user_id)
    except UserNotFoundError:
        raise credentials_exception

    request.state.principal = f"user:{user.id}"
    return user


def require_scope(scope: str):
    """Dependency factory for routes readable by humans always, services by scope.

    Service principals need ``scope`` in their grant (e.g. ``incidents:read``);
    human users keep their existing access unchanged.
    """

    def _dependency(
        principal: UserPublic | ServicePrincipal = Depends(get_reader_principal),
    ) -> UserPublic | ServicePrincipal:
        if isinstance(principal, ServicePrincipal) and scope not in principal.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient scope",
            )
        return principal

    return _dependency


def require_self_or_admin(current_user: UserPublic, user_id: int) -> None:
    """Raise 403 unless the caller is the target user or an admin."""
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
