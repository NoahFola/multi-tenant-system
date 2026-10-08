from fastapi import Depends
from common.firestore_client import get_db
from common.redis_client import get_redis
from app.core.email import SmtpEmailSender
from app.services.auth_service import AuthService

def get_auth_service(
    db=Depends(get_db),
    redis=Depends(get_redis)
) -> AuthService:
    return AuthService(db=db, email=SmtpEmailSender(), redis=redis)
