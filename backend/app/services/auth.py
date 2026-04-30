"""
Auth Service
------------
Password hashing, JWT creation/verification, and DB-level
register/login logic. All crypto lives here — no other module
should import jose or passlib directly.
"""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.db import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

log = structlog.get_logger()

# bcrypt is slow by design — that's what makes it secure for passwords
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pre-computed at import time so login_user has a valid hash to verify against
# when the email doesn't exist (prevents timing-based user enumeration).
_DUMMY_HASH = _pwd_context.hash("_dummy_")


# ── Password helpers ───────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT helpers ────────────────────────────────────────────────────────────────

def create_access_token(user_id: uuid.UUID, email: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """
    Verify and decode a JWT. Raises JWTError if invalid or expired.
    The API dependency layer catches JWTError and returns 401.
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


# ── DB operations ──────────────────────────────────────────────────────────────

async def register_user(session: AsyncSession, request: RegisterRequest) -> TokenResponse:
    # Check email uniqueness before inserting
    existing = await session.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        webhook_email=request.webhook_email,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    log.info("auth.register", user_id=str(user.id), email=user.email)
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


async def login_user(session: AsyncSession, request: LoginRequest) -> TokenResponse:
    result = await session.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    # Use a constant-time comparison path — don't short-circuit on missing user
    # to prevent timing-based user enumeration attacks
    password_hash = user.password_hash if user else _DUMMY_HASH

    if not verify_password(request.password, password_hash) or not user:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    log.info("auth.login", user_id=str(user.id))
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
