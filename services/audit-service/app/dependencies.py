from fastapi import Depends
from common.firestore_client import get_db
from common.redis_client import get_redis
from app.services.audit_service import AuditService

def get_audit_service(
    db=Depends(get_db),
    redis=Depends(get_redis),
) -> AuditService:
    return AuditService(db=db, redis=redis)
