from fastapi import APIRouter, Depends
from app.schemas import ForgotPasswordRequest, ResetPasswordRequest
from app.dependencies import get_auth_service
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, svc: AuthService = Depends(get_auth_service)):
    return svc.forgot_password(req)

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, svc: AuthService = Depends(get_auth_service)):
    return svc.reset_password(req)
