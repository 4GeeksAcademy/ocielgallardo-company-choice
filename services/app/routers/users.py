from fastapi import APIRouter, HTTPException

from services.app.domain.user_service import create_user
from services.app.models.user import UserCreate, UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserPublic, status_code=201)
def register_user(payload: UserCreate):
    try:
        return create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))