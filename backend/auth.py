"""
auth.py
JWT creation, verification and FastAPI dependency.
Uses Python stdlib hashlib for password hashing — no passlib/bcrypt dependency.
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
import models

settings     = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Password hashing (stdlib only — no bcrypt/passlib) ───────────────
def hash_password(plain: str) -> str:
    """PBKDF2-SHA256 with 32-byte random salt, 260000 iterations."""
    salt = os.urandom(32)
    key  = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 260000)
    return f"pbkdf2${salt.hex()}${key.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    """Verify plain text against a stored pbkdf2$salt$hash string."""
    try:
        scheme, salt_hex, key_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        salt  = bytes.fromhex(salt_hex)
        key   = bytes.fromhex(key_hex)
        check = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 260000)
        return hmac.compare_digest(check, key)
    except Exception:
        return False


# ── JWT ──────────────────────────────────────────────────────────────
def create_access_token(user_id: UUID, email: str) -> str:
    expire  = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependency ────────────────────────────────────────────────
def get_current_user(
    token: str        = Depends(oauth2_scheme),
    db:    Session    = Depends(get_db),
) -> models.User:
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub")
    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.is_active == True,
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user