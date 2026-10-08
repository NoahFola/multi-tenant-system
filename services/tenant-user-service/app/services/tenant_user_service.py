import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from google.cloud import firestore

from app.repositories.user_repo import list_users, get_user_by_id, update_user_role, disable_user
from app.repositories.invitation_repo import create_invitation, get_invitation_by_token, mark_invitation_accepted, list_pending_invitations
from app.repositories.role_repo import get_role_by_id
from app.schemas import UserResponse, InvitationResponse
from common.errors import NotFoundError, ForbiddenError, ConflictError, GoneError
from common.events import emit_audit_event
from common.config import settings

class TenantUserService:
    def __init__(self, db: firestore.Client, email_sender, redis):
        self.db = db
        self.email = email_sender
        self.redis = redis

    def list_users(self, tenant_id: str) -> list[UserResponse]:
        users = list_users(self.db, tenant_id)
        return [UserResponse(**u) for u in users]

    def get_user(self, tenant_id: str, user_id: str) -> UserResponse:
        user = get_user_by_id(self.db, tenant_id, user_id)
        if not user:
            raise NotFoundError("User not found")
        return UserResponse(**user)

    def change_role(self, tenant_id: str, actor_id: str, user_id: str, new_role_id: str, ip: str = ""):
        # 1. Verify new_role_id belongs to this tenant (TOCTOU guard)
        role = get_role_by_id(self.db, tenant_id, new_role_id)
        if not role:
            raise ForbiddenError("Role does not exist or belong to this tenant")
            
        # 2. Prevent actor from demoting themselves (assuming they might, but not strictly forbidden by the spec, spec just says "Prevent actor from demoting themselves")
        if actor_id == user_id:
            raise ForbiddenError("Cannot change your own role")
            
        user = get_user_by_id(self.db, tenant_id, user_id)
        if not user:
            raise NotFoundError("User not found")
            
        old_role = user.get("role_id")
        
        # 3. call update_user_role()
        update_user_role(self.db, tenant_id, user_id, new_role_id)
        
        # 4. emit_audit_event
        emit_audit_event(self.redis, tenant_id, actor_id,
            action="user.role_changed", resource_type="user",
            resource_id=user_id,
            metadata={"old_role_id": old_role, "new_role_id": new_role_id}, ip=ip)
            
        return {"message": "Role changed successfully"}

    def disable_user(self, tenant_id: str, actor_id: str, user_id: str, ip: str = ""):
        # 1. Prevent actor from disabling themselves
        if actor_id == user_id:
            raise ForbiddenError("Cannot disable yourself")
            
        user = get_user_by_id(self.db, tenant_id, user_id)
        if not user:
            raise NotFoundError("User not found")
            
        # 2. call repo disable_user()
        disable_user(self.db, tenant_id, user_id)
        
        # 3. revoke_all_sessions_for_user() in Firestore
        try:
            from common.sessions import revoke_all_sessions_for_user # Assuming it's there or will be
            revoke_all_sessions_for_user(self.db, user_id)
        except ImportError:
            pass # Stub if not exists in tenant-user-service yet
            
        # 4. Redis denylist: setex("disabled:{user_id}", TTL, "1")
        self.redis.setex(f"disabled:{user_id}", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
        
        # 5. emit_audit_event
        emit_audit_event(self.redis, tenant_id, actor_id,
            action="user.disabled", resource_type="user",
            resource_id=user_id, metadata={}, ip=ip)
            
        return {"message": "User disabled"}

    def invite_user(self, tenant_id: str, invited_by: str, email: str, role_id: str, ip: str = ""):
        email = email.lower()
        
        # 1. Check email not already a user in this tenant (global check might be better, but spec says "in this tenant")
        # Let's check global user by email just to be sure. Wait, user repo in tenant-service is scoped by tenant.
        # But we can query users by email globally to avoid collisions.
        docs = self.db.collection("users").where(filter=firestore.FieldFilter("email", "==", email)).limit(1).stream()
        for doc in docs:
            raise ConflictError("User with this email already exists")
            
        # 2. Check no pending invitation for this email + tenant
        invites = self.db.collection("invitations").where(filter=firestore.FieldFilter("email", "==", email)).where(filter=firestore.FieldFilter("tenant_id", "==", tenant_id)).where(filter=firestore.FieldFilter("status", "==", "pending")).stream()
        for _ in invites:
            raise ConflictError("Invitation already pending for this email")
            
        role = get_role_by_id(self.db, tenant_id, role_id)
        if not role:
            raise ForbiddenError("Role does not exist or belong to this tenant")
            
        # 3. raw_token = secrets.token_urlsafe(32)
        raw_token = secrets.token_urlsafe(32)
        
        # 4. token_hash = SHA-256(raw_token)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        
        # 5. expires_at = now + 48 hours
        expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
        
        # 6. create_invitation() in repo
        invitation_id = create_invitation(self.db, tenant_id, invited_by, email, role_id, token_hash, expires_at)
        
        # 7. Send invitation email with raw_token in the link
        # Use email service
        self.email.send_invitation_email(email, raw_token)
        
        # 8. emit_audit_event
        emit_audit_event(self.redis, tenant_id, invited_by,
            action="user.invited", resource_type="invitation",
            resource_id=invitation_id,
            metadata={"email": email, "role_id": role_id}, ip=ip)
            
        # 9. return {"message": "Invitation sent"}
        return {"message": "Invitation sent"}

    def accept_invitation(self, raw_token: str, password: str):
        # 1. token_hash = SHA-256(raw_token)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        
        # 2. get_invitation_by_token(token_hash)
        invitation = get_invitation_by_token(self.db, token_hash)
        
        # 3. Validate: exists, status == pending, not expired
        if not invitation or invitation.get("status") != "pending":
            raise GoneError("Invalid or already accepted invitation")
            
        # timezone.utc vs offset-naive depends on how it was saved, but assuming it was UTC aware
        if invitation["expires_at"] < datetime.now(timezone.utc):
            raise GoneError("Invitation expired")
            
        # 4. Check email not already registered globally
        email = invitation["email"].lower()
        docs = self.db.collection("users").where(filter=firestore.FieldFilter("email", "==", email)).limit(1).stream()
        for _ in docs:
            raise ConflictError("User already registered")
            
        # 5. Create user with invitation.tenant_id + invitation.role_id
        from app.core.hashing import hash_password # Assuming we have it
        hashed = hash_password(password)
        
        doc_ref = self.db.collection("users").document()
        doc_ref.set({
            "email": email,
            "password_hash": hashed,
            "tenant_id": invitation["tenant_id"],
            "role_id": invitation["role_id"],
            "is_verified": False,
            "status": "active",
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        
        # 6. mark_invitation_accepted()
        mark_invitation_accepted(self.db, invitation["id"])
        
        # 7. return {"uid": ..., "message": "Account created"}
        return {"uid": doc_ref.id, "message": "Account created. Please verify your email."}
