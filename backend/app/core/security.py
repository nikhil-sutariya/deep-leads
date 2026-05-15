from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError
from app.core.config import get_settings
from fastapi.security import OAuth2PasswordBearer

settings = get_settings()

# OAuth2 scheme for Swagger UI (optional, falls back to cookies)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/swagger-login",
    auto_error=False  # Don't auto-error, we'll handle it manually
)

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
	return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
	return pwd_context.hash(password)

def create_access_token(user_id: str, duration: int = settings.access_token_expire_minutes) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=duration)
    payload = {"id": user_id, "exp": expire.timestamp()}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.oauth_algorithm)

def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"id": user_id, "exp": expire.timestamp(), "refresh": True}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.oauth_algorithm)

def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.oauth_algorithm])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
