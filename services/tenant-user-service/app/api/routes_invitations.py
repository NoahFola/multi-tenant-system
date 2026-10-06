from fastapi import APIRouter, Depends
from app.schemas import InviteRequest, AcceptInvitationRequest, InvitationResponse
from app.services.tenant_user_service import TenantUserService
from common.permissions import require_permission, Permission
from app.dependencies import get_tenant_user_service

router = APIRouter()

@router.post("")
def invite_user(
    req: InviteRequest,
    actor: dict = Depends(require_permission(Permission.USER_INVITE)),
    svc: TenantUserService = Depends(get_tenant_user_service),
):
    tenant_id = actor["tenant_id"]
    invited_by = actor["sub"]
    return svc.invite_user(tenant_id, invited_by, req.email, req.role_id)

@router.get("", response_model=list[InvitationResponse])
def list_pending_invitations(
    actor: dict = Depends(require_permission(Permission.USER_INVITE)),
    svc: TenantUserService = Depends(get_tenant_user_service),
):
    # Depending on how TenantUserService exposes it. Let's assume it exists or call repo directly.
    # The spec did not explicitly define `list_pending_invitations` in TenantUserService,
    # but the repo has it. I'll add it to the service or call the repo here.
    # For now, let's call the repo directly since we have the db.
    from app.repositories.invitation_repo import list_pending_invitations
    invites = list_pending_invitations(svc.db, actor["tenant_id"])
    return [InvitationResponse(**i) for i in invites]

@router.post("/accept")
def accept_invitation(
    req: AcceptInvitationRequest,
    svc: TenantUserService = Depends(get_tenant_user_service),
):
    return svc.accept_invitation(req.token, req.password)
