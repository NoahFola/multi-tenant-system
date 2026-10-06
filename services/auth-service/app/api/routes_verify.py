from fastapi import APIRouter, Depends
from app.dependencies import get_auth_service
from app.services.auth_service import AuthService

router = APIRouter()

@router.get("/verify-email")
def verify_email(code: str, svc: AuthService = Depends(get_auth_service)):
    return svc.verify_email(code)
