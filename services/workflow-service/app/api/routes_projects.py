from fastapi import APIRouter, Depends
from common.permissions import require_permission, Permission
from app.dependencies import get_workflow_service
from app.services.workflow_service import WorkflowService
from app.schemas import ProjectCreate, ProjectResponse

router = APIRouter()

@router.post("", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    actor: dict = Depends(require_permission(Permission.WORKFLOW_SUBMIT)),
    svc: WorkflowService = Depends(get_workflow_service),
):
    return svc.create_project(
        tenant_id=actor["tenant_id"],
        actor_id=actor["sub"],
        name=project.name,
    )

@router.get("", response_model=list[ProjectResponse])
def list_projects(
    actor: dict = Depends(require_permission(Permission.WORKFLOW_SUBMIT)),
    svc: WorkflowService = Depends(get_workflow_service),
):
    return svc.list_projects(tenant_id=actor["tenant_id"])
