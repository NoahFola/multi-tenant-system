from fastapi import APIRouter, Depends
from datetime import datetime
from common.permissions import require_permission, Permission
from app.dependencies import get_audit_service
from app.services.audit_service import AuditService
from app.schemas.audit_schemas import AuditLogListResponse

router = APIRouter()

@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    actor_id: str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    current_user: dict = Depends(require_permission(Permission.AUDIT_READ)),
    svc: AuditService = Depends(get_audit_service),
):
    entries = svc.list_logs(
        tenant_id=current_user["tenant_id"],
        actor_id=actor_id,
        action=action,
        date_from=date_from,
        date_to=date_to
    )
    return {"entries": entries, "total": len(entries)}
