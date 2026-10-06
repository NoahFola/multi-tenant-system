from fastapi import APIRouter, Depends
from app.schemas import UserResponse, ChangeRoleRequest
from app.services.tenant_user_service import TenantUserService
from common.permissions import require_permission, Permission
# Assuming get_tenant_user_service is defined in app.dependencies
from app.dependencies import get_tenant_user_service

router = APIRouter()

@router.get("", response_model=list[UserResponse])
def list_users(
    actor: dict = Depends(require_permission(Permission.USER_LIST)),
    svc: TenantUserService = Depends(get_tenant_user_service),
):
    return svc.list_users(actor["tenant_id"])

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    actor: dict = Depends(require_permission(Permission.USER_LIST)),
    svc: TenantUserService = Depends(get_tenant_user_service),
):
    return svc.get_user(actor["tenant_id"], user_id)

@router.patch("/{user_id}/role")
def change_role(
    user_id: str,
    req: ChangeRoleRequest,
    actor: dict = Depends(require_permission(Permission.USER_ROLE_CHANGE)),
    svc: TenantUserService = Depends(get_tenant_user_service),
):
    tenant_id = actor["tenant_id"]
    actor_id  = actor["sub"]
    return svc.change_role(tenant_id, actor_id, user_id, req.role_id)

@router.post("/{user_id}/disable")
def disable_user(
    user_id: str,
    actor: dict = Depends(require_permission(Permission.USER_DISABLE)),
    svc: TenantUserService = Depends(get_tenant_user_service),
):
    tenant_id = actor["tenant_id"]
    actor_id  = actor["sub"]
    return svc.disable_user(tenant_id, actor_id, user_id)
