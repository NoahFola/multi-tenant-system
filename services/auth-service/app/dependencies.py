from functools import lru_cache
from common.firestore_client import get_db
from app.core.email import SmtpEmailSender
from app.services.auth_service import AuthService

@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(db=get_db(), email=SmtpEmailSender())
