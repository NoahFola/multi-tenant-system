import hashlib
from datetime import datetime, timezone
from google.cloud import firestore

from common.errors import ConflictError, UnauthorizedError, ForbiddenError, GoneError
from app.schemas import (
    RegisterRequest, RegisterResponse, LoginRequest, TokenResponse, 
    RefreshRequest, LogoutRequest, ForgotPasswordRequest, ResetPasswordRequest
)
from app.repositories.user_repo import get_user_by_email, create_user, get_user_by_id, update_user
from app.repositories.tenant_repo import create_tenant, seed_roles
from app.repositories.token_repo import create_verification_token, get_verification_token, create_reset_token, get_reset_token
from app.core.hashing import hash_password, verify_password
from app.core.tokens import create_access_token, create_refresh_token
from app.core.sessions import (
    create_session, get_session_by_refresh_any, revoke_session, 
    revoke_family, revoke_all_sessions_for_user
)
from app.core.email_protocol import EmailSender

class AuthService:
    def __init__(self, db: firestore.Client, email: EmailSender):
        self.db = db
        self.email = email

    def register(self, req: RegisterRequest) -> RegisterResponse:
        email = req.email.lower()
        
        existing = get_user_by_email(self.db, email)
        if existing:
            raise ConflictError("Email already registered")
            
        hashed = hash_password(req.password)
        
        batch = self.db.batch()
        tenant_id = create_tenant(self.db, req.company_name, batch=batch)
        role_ids = seed_roles(self.db, tenant_id, batch=batch)
        uid = create_user(self.db, email, hashed, tenant_id=tenant_id, role_id=role_ids["admin"], batch=batch)
        batch.commit()
        
        raw_code = create_verification_token(self.db, uid)
        self.email.send_verification_email(email, raw_code)
        
        return RegisterResponse(uid=uid, message="Verification email sent")

    def login(self, req: LoginRequest) -> TokenResponse:
        user = get_user_by_email(self.db, req.email.lower())
        
        if not user or not verify_password(req.password, user["password_hash"]):
            raise UnauthorizedError("Invalid email or password")
            
        if not user.get("is_verified", False):
            raise ForbiddenError("Email not verified")
            
        raw_refresh = create_refresh_token()
        create_session(self.db, user["uid"], raw_refresh)
        
        role_doc = self.db.collection("roles").document(user["role_id"]).get()
        role_name = role_doc.to_dict()["name"]
        
        access = create_access_token(
            user["uid"], user["email"],
            tenant_id=user["tenant_id"],
            role=role_name
        )
        
        return TokenResponse(access_token=access, refresh_token=raw_refresh)

    def refresh(self, req: RefreshRequest) -> TokenResponse:
        session = get_session_by_refresh_any(self.db, req.refresh_token)
        
        if not session:
            raise UnauthorizedError("Invalid refresh token")
            
        if session["revoked"]:
            revoke_family(self.db, session["family"])
            raise UnauthorizedError("Session invalidated due to token reuse")
            
        if session["expires_at"] < datetime.now(timezone.utc):
            raise UnauthorizedError("Refresh token expired")
            
        revoke_session(self.db, session["session_id"])
        
        user = get_user_by_id(self.db, session["uid"])
        if not user:
            raise UnauthorizedError("User no longer exists")
            
        raw_refresh = create_refresh_token()
        parent_hash = hashlib.sha256(req.refresh_token.encode("utf-8")).hexdigest()
        create_session(self.db, session["uid"], raw_refresh, family=session["family"], parent_hash=parent_hash)
        
        role_doc = self.db.collection("roles").document(user["role_id"]).get()
        role_name = role_doc.to_dict()["name"]
        
        access = create_access_token(
            session["uid"], user["email"],
            tenant_id=user["tenant_id"],
            role=role_name
        )
        
        return TokenResponse(access_token=access, refresh_token=raw_refresh)

    def logout(self, req: LogoutRequest, current_user: dict) -> dict:
        session = get_session_by_refresh_any(self.db, req.refresh_token)
        
        if session and session["uid"] == current_user["sub"]:
            revoke_session(self.db, session["session_id"])
            
        return {"message": "Logged out"}

    def forgot_password(self, req: ForgotPasswordRequest) -> dict:
        user = get_user_by_email(self.db, req.email.lower())
        
        if user:
            raw_code = create_reset_token(self.db, user["uid"])
            self.email.send_password_reset_email(req.email, raw_code)
            
        return {"message": "If that email is registered, a reset link was sent."}

    def reset_password(self, req: ResetPasswordRequest) -> dict:
        token = get_reset_token(self.db, req.code)
        
        if not token or token["used"] or token["expires_at"] < datetime.now(timezone.utc):
            raise GoneError("Invalid or expired code")
            
        batch = self.db.batch()
        
        # Mark token used
        token_ref = self.db.collection("password_reset_tokens").document(token["token_id"])
        batch.update(token_ref, {"used": True})
        
        # Update user password
        user_ref = self.db.collection("users").document(token["uid"])
        hashed = hash_password(req.new_password)
        batch.update(user_ref, {"password_hash": hashed})
        
        batch.commit()
        
        # Revoke all sessions
        revoke_all_sessions_for_user(self.db, token["uid"])
        
        return {"message": "Password updated successfully"}

    def verify_email(self, code: str) -> dict:
        token = get_verification_token(self.db, code)
        
        if not token:
            raise GoneError("Invalid or already used code")
            
        if token["used"]:
            raise GoneError("Invalid or already used code")
            
        if token["expires_at"] < datetime.now(timezone.utc):
            raise GoneError("Code expired")
            
        batch = self.db.batch()
        
        token_ref = self.db.collection("verification_tokens").document(token["token_id"])
        batch.update(token_ref, {"used": True})
        
        user_ref = self.db.collection("users").document(token["uid"])
        batch.update(user_ref, {"is_verified": True})
        
        batch.commit()
        
        return {"message": "Email verified"}
