from fastapi import APIRouter, Depends, HTTPException

from services.app.core.deps import get_current_user, require_self_or_admin
from services.app.domain.user_service import (
    create_user,
    list_users,
    get_user_by_id,
    update_user,
    delete_user,
    UserNotFoundError,
)
from services.app.models.user import (
    DetailResponse,
    RegisterResponse,
    UserCreate,
    UserPublic,
    UserUpdate,
    UserRole,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=RegisterResponse, status_code=201)
def register_user(payload: UserCreate):
    try:
        user = create_user(payload)
        return RegisterResponse(
            id=user.id,
            is_active=user.is_active,
            role=user.role,
            created_at=user.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("", response_model=list[UserPublic])
def list_users_endpoint(
    _current_user: UserPublic = Depends(get_current_user),
):
    return list_users()


@router.get("/{user_id}", response_model=UserPublic)
def get_user_endpoint(
    user_id: int,
    _current_user: UserPublic = Depends(get_current_user),
):
    try:
        return get_user_by_id(user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.put("/{user_id}", response_model=UserPublic)
def update_user_endpoint(
    user_id: int,
    payload: UserUpdate,
    current_user: UserPublic = Depends(get_current_user),
):
    require_self_or_admin(current_user, user_id)
    if payload.role is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        return update_user(user_id, payload)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.delete("/{user_id}", response_model=DetailResponse, status_code=200)
def delete_user_endpoint(
    user_id: int,
    current_user: UserPublic = Depends(get_current_user),
):
    require_self_or_admin(current_user, user_id)
    try:
        delete_user(user_id)
        return DetailResponse(detail="User deleted")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
