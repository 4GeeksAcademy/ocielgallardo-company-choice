from fastapi import APIRouter, HTTPException
from fastapi import Depends

from services.app.domain.user_service import authenticate_user, InvalidCredentialsError
from services.app.models.user import LoginRequest, TokenResponse  # o donde los hayas puesto
from services.app.core.deps import get_current_user
from services.app.domain.profile_service import get_profile_by_user_id, ProfileNotFoundError
from services.app.models.user import UserPublic
# y un response model si quieres; de momento un dict vale para probar

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    try:
        token = authenticate_user(str(payload.email), payload.password)
        return TokenResponse(access_token=token)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

@router.get("/me")
def read_me(current_user: UserPublic = Depends(get_current_user)):
    try:
        profile = get_profile_by_user_id(current_user.id)
    except ProfileNotFoundError:
        profile = None
    return {
        "email": current_user.email,
        "role": current_user.role,
        "profile": profile,
    }