"""
FastAPI Dependencies
--------------------
Reusable Depends() callables injected into route functions.

- get_session : yields a request-scoped AsyncSession
- get_current_user : validates the JWT and returns the User ORM object
"""

import uuid
from typing import AsyncIterator

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionFactory
from app.models.db import User
from app.services.auth import decode_token, get_user_by_id

log = structlog.get_logger()

# Extracts the Bearer token from the Authorization header
_bearer = HTTPBearer()


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Yields one AsyncSession per request, then commits or rolls back on exit.
    Use with: session: AsyncSession = Depends(get_session)
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Validates the JWT from the Authorization: Bearer <token> header.
    Returns the User ORM object or raises 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_id(session, uuid.UUID(user_id))
    if not user:
        raise credentials_exception

    return user
