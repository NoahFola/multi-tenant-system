from fastapi import APIRouter, Depends
from common.security import get_current_user
from app.schemas import RegisterRequest, RegisterResponse, LoginRequest, TokenResponse, RefreshRequest, LogoutRequest
from app.dependencies import get_auth_service
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/register", response_model=RegisterResponse)
def register(req: RegisterRequest, svc: AuthService = Depends(get_auth_service)):
    return svc.register(req)

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, svc: AuthService = Depends(get_auth_service)):
    return svc.login(req)

@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, svc: AuthService = Depends(get_auth_service)):
    return svc.refresh(req)

@router.post("/logout")
def logout(req: LogoutRequest, user: dict = Depends(get_current_user), svc: AuthService = Depends(get_auth_service)):
    return svc.logout(req, user)
