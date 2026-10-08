from fastapi import APIRouter, Depends
from common.permissions import require_permission, Permission
from common.firestore_client import get_db
from app.repositories.notification_repo import list_notifications, mark_read
from common.errors import NotFoundError

router = APIRouter()

@router.get("")
def get_notifications(
    actor: dict = Depends(require_permission(Permission.WORKFLOW_SUBMIT)),
    db = Depends(get_db),
):
    return list_notifications(db, actor["tenant_id"], actor["sub"])

@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    actor: dict = Depends(require_permission(Permission.WORKFLOW_SUBMIT)),
    db = Depends(get_db),
):
    ok = mark_read(db, notification_id, actor["tenant_id"], actor["sub"])
    if not ok:
        raise NotFoundError("Notification not found")
    return {"message": "marked as read"}
