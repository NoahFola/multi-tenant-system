from fastapi import Depends
from common.security import get_current_user
from common.errors import ForbiddenError

class Permission:
    WORKFLOW_SUBMIT  = "workflow:submit"
    WORKFLOW_REVIEW  = "workflow:review"
    WORKFLOW_APPROVE = "workflow:approve"
    WORKFLOW_REJECT  = "workflow:reject"
    USER_INVITE      = "user:invite"
    USER_LIST        = "user:list"
    USER_ROLE_CHANGE = "user:role_change"
    USER_DISABLE     = "user:disable"

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "employee": [Permission.WORKFLOW_SUBMIT],
    "manager":  [Permission.WORKFLOW_SUBMIT, Permission.WORKFLOW_REVIEW,
                 Permission.WORKFLOW_APPROVE, Permission.WORKFLOW_REJECT],
    "admin":    [Permission.WORKFLOW_SUBMIT, Permission.WORKFLOW_REVIEW,
                 Permission.WORKFLOW_APPROVE, Permission.WORKFLOW_REJECT,
                 Permission.USER_INVITE, Permission.USER_LIST,
                 Permission.USER_ROLE_CHANGE, Permission.USER_DISABLE],
}

def require_permission(permission: str):
    """
    FastAPI dependency factory.
    Usage: Depends(require_permission("user:invite"))
    """
    async def _check(current_user: dict = Depends(get_current_user)) -> dict:
        role = current_user.get("role", "")
        allowed = ROLE_PERMISSIONS.get(role, [])
        if permission not in allowed:
            raise ForbiddenError(
                f"Role '{role}' does not have permission '{permission}'"
            )
        return current_user
    return _check
