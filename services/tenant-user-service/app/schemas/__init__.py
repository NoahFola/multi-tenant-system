from pydantic import BaseModel, EmailStr
from datetime import datetime

class InviteRequest(BaseModel):
    email: EmailStr
    role_id: str

class AcceptInvitationRequest(BaseModel):
    token: str
    password: str

class ChangeRoleRequest(BaseModel):
    role_id: str

class UserResponse(BaseModel):
    id: str
    email: str
    role_id: str
    status: str
    created_at: datetime

class InvitationResponse(BaseModel):
    id: str
    email: str
    role_id: str
    status: str
    expires_at: datetime
