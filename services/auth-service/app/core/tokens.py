import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from common.config import settings
import uuid
from common.errors import UnauthorizedError

def create_access_token(uid: str, email: str, tenant_id: str, role: str) -> str:
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": uid,
        "email": email,
        "tenant_id": tenant_id,
        "role": role,
        "type": "access",
        "exp": expire,
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        return payload
    except ExpiredSignatureError:
        raise UnauthorizedError("Token expired")
    except JWTError:
        raise UnauthorizedError("Invalid token")
