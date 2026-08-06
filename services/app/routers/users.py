from fastapi import APIRouter, HTTPException

from services.app.domain.user_service import (
    create_user,
    list_users,
    get_user_by_id,
    UserNotFoundError,
    #update_user,
    #delete_user,
)

from services.app.models.user import UserCreate, UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserPublic, status_code=201)
def register_user(payload: UserCreate):
    try:
        return create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

@router.get("", response_model=list[UserPublic])
def list_users_endpoint():
    return list_users()

@router.get("/{user_id}", response_model=UserPublic)
def get_user_endpoint(user_id: int):
    try:
        return get_user_by_id(user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

# Patch /users/{id}

# Delete /users/{id}