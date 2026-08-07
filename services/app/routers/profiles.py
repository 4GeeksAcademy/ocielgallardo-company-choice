from fastapi import APIRouter, Depends, HTTPException

from services.app.core.deps import get_current_user
from services.app.domain.profile_service import (
    get_profile_by_user_id,
    update_profile_by_user_id,
    ProfileNotFoundError,
)
from services.app.models.profile import ProfilePublic, ProfileUpdate
from services.app.models.user import UserPublic

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=ProfilePublic)
def read_my_profile(current_user: UserPublic = Depends(get_current_user)):
    try:
        return get_profile_by_user_id(current_user.id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail="Profile not found")


@router.put("/me", response_model=ProfilePublic)
def update_my_profile(
    payload: ProfileUpdate,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        return update_profile_by_user_id(current_user.id, payload)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail="Profile not found")