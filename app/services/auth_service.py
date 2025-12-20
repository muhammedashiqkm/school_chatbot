from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain password against the stored hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generates a bcrypt hash for the password."""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(subject: Union[str, Any], expires_delta: timedelta | None = None) -> str:
        """
        Creates a JWT access token.
        Uses timezone-aware UTC datetime to comply with Python 3.12+ standards.
        """
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
        
        to_encode = {
            "sub": str(subject), 
            "exp": expire,
            "iat": now
        }
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt