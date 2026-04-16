import os
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import JWTError, jwt

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT config from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-before-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str) -> str:
    """
    Create a JWT token containing the user's ID and email.
    Expires after EXPIRATION_MINUTES (default 60).
    """
    expire = datetime.utcnow() + timedelta(minutes=EXPIRATION_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.
    Returns the payload dict if valid, None if expired or tampered.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None