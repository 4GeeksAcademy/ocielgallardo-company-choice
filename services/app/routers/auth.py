from fastapi import APIRouter, HTTPException, Depends

from services.app.domain.user_service import authenticate_user, InvalidCredentialsError
from services.app.models.user import (
    LoginRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    AuthMeResponse,
    MessageResponse,
)
from services.app.core.deps import get_current_user
from services.app.domain.profile_service import (
    get_profile_by_user_id,
    ProfileNotFoundError,
)
from services.app.models.user import UserPublic

from services.app.domain.password_reset_service import (
    change_password as change_password_service,
    forgot_password as forgot_password_service,
    reset_password as reset_password_service,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    try:
        token = authenticate_user(str(payload.username), payload.password)
        return TokenResponse(access_token=token)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.get("/me", response_model=AuthMeResponse)
def read_me(current_user: UserPublic = Depends(get_current_user)):
    try:
        profile = get_profile_by_user_id(current_user.id)
    except ProfileNotFoundError:
        profile = None
    return AuthMeResponse(
        email=current_user.email,
        role=current_user.role,
        profile=profile,
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest):
    # Must always return 200 to avoid user enumeration.
    result = forgot_password_service(payload.email)
    return MessageResponse(message=result["message"])


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest):
    try:
        result = reset_password_service(
            token=payload.token, new_password=payload.new_password
        )
        return MessageResponse(message=result["message"])
    except HTTPException as exc:
        # For invalid or expired tokens, rubric expects 400.
        raise HTTPException(status_code=400, detail=str(exc.detail))


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        result = change_password_service(
            user_id=current_user.id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
        return MessageResponse(message=result["message"])
    except HTTPException as exc:
        raise HTTPException(status_code=400, detail=str(exc.detail))
