from fastapi import Depends
from common.firestore_client import get_db
from common.redis_client import get_redis
from app.services.workflow_service import WorkflowService

def get_workflow_service(
    db=Depends(get_db),
    redis=Depends(get_redis),
) -> WorkflowService:
    return WorkflowService(db=db, redis=redis)
