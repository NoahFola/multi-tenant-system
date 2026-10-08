from fastapi import APIRouter, Depends, Header
from common.permissions import require_permission, Permission
from app.dependencies import get_workflow_service
from app.services.workflow_service import WorkflowService
from app.schemas import WorkflowCreate
from pydantic import BaseModel

router = APIRouter()

@router.post("")
def submit(
    workflow: WorkflowCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    actor: dict = Depends(require_permission(Permission.WORKFLOW_SUBMIT)),
    svc: WorkflowService = Depends(get_workflow_service),
):
    return svc.submit(
        tenant_id=actor["tenant_id"],
        actor_id=actor["sub"],
        project_id=workflow.project_id,
        title=workflow.title,
        idempotency_key=idempotency_key
    )

@router.post("/{workflow_id}/review")
def start_review(
    workflow_id: str,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    actor: dict = Depends(require_permission(Permission.WORKFLOW_APPROVE)),
    svc: WorkflowService = Depends(get_workflow_service),
):
    return svc.start_review(
        tenant_id=actor["tenant_id"],
        actor_id=actor["sub"],
        workflow_id=workflow_id,
        idempotency_key=idempotency_key
    )

class ActionRequest(BaseModel):
    expected_version: int

@router.post("/{workflow_id}/approve")
def approve(
    workflow_id: str,
    payload: ActionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    actor: dict = Depends(require_permission(Permission.WORKFLOW_APPROVE)),
    svc: WorkflowService = Depends(get_workflow_service),
):
    return svc.approve(
        tenant_id=actor["tenant_id"],
        actor_id=actor["sub"],
        workflow_id=workflow_id,
        expected_version=payload.expected_version,
        idempotency_key=idempotency_key
    )

@router.post("/{workflow_id}/reject")
def reject(
    workflow_id: str,
    payload: ActionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    actor: dict = Depends(require_permission(Permission.WORKFLOW_APPROVE)),
    svc: WorkflowService = Depends(get_workflow_service),
):
    return svc.reject(
        tenant_id=actor["tenant_id"],
        actor_id=actor["sub"],
        workflow_id=workflow_id,
        expected_version=payload.expected_version,
        idempotency_key=idempotency_key
    )

@router.get("/{workflow_id}")
def get_workflow(
    workflow_id: str,
    actor: dict = Depends(require_permission(Permission.WORKFLOW_SUBMIT)),
    svc: WorkflowService = Depends(get_workflow_service),
):
    return svc.get_workflow(tenant_id=actor["tenant_id"], workflow_id=workflow_id)

@router.get("/{workflow_id}/history")
def get_history(
    workflow_id: str,
    actor: dict = Depends(require_permission(Permission.WORKFLOW_SUBMIT)),
    svc: WorkflowService = Depends(get_workflow_service),
):
    return svc.get_history(tenant_id=actor["tenant_id"], workflow_id=workflow_id)
