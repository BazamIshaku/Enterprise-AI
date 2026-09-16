"""Password and signed-token helpers."""
from datetime import UTC, datetime, timedelta
import os
import jwt
from pwdlib import PasswordHash

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-local-development-secret")
JWT_ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(hours=8)
    return jwt.encode({"sub": user_id, "exp": expires_at}, JWT_SECRET, algorithm=JWT_ALGORITHM)
