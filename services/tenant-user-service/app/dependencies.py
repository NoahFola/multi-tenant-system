from fastapi import Depends
from common.firestore_client import get_db
from common.redis_client import get_redis
from app.services.tenant_user_service import TenantUserService

# Since tenant-user-service doesn't handle full auth/emailing directly in this step,
# We'll use a dummy EmailSender or just a simple class that logs, unless there's a real one.
class DummyEmailSender:
    def send_invitation_email(self, email: str, token: str):
        print(f"Sending invitation to {email} with token {token}")

def get_tenant_user_service(
    db = Depends(get_db),
    redis = Depends(get_redis)
) -> TenantUserService:
    return TenantUserService(db=db, email_sender=DummyEmailSender(), redis=redis)
