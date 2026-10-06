from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from common.config import settings
from common.errors import UnauthorizedError

bearer_scheme = HTTPBearer()

def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        return payload
    except ExpiredSignatureError:
        raise UnauthorizedError("Token expired")
    except JWTError:
        raise UnauthorizedError("Invalid token")

from common.redis_client import get_redis

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    redis = Depends(get_redis)
) -> dict:
    payload = verify_access_token(credentials.credentials)
    uid = payload["sub"]
    if redis.exists(f"disabled:{uid}"):
        raise ForbiddenError("Account has been disabled")
    return payload
