from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AuditLogEntry(BaseModel):
    """
    Immutable log entry. Never expose password_hash or tokens in `details`.
    """
    log_id: str
    event_id: str
    tenant_id: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    timestamp: datetime
    ip: str = ""
    success: bool = True
    details: dict = Field(default_factory=dict)
    prev_hash: Optional[str] = None

class AuditLogListResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int
