from fastapi import APIRouter, HTTPException

from services.app.domain.user_service import authenticate_user, InvalidCredentialsError
from services.app.models.user import LoginRequest, TokenResponse  # o donde los hayas puesto

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    try:
        token = authenticate_user(str(payload.email), payload.password)
        return TokenResponse(access_token=token)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc))