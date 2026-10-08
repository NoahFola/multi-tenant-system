from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str

class ProjectResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    created_by: str

class WorkflowCreate(BaseModel):
    project_id: str
    title: str
