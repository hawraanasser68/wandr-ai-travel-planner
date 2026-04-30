"""
Async SQLAlchemy engine and session factory.
The engine is created once (managed by the FastAPI lifespan) — not per-request.
Every route gets a short-lived AsyncSession via the get_db() dependency.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# pool_pre_ping=True drops stale connections before handing them to a request
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# expire_on_commit=False keeps objects usable after a commit inside async code
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# All ORM models inherit from this Base so Alembic can find them
class Base(DeclarativeBase):
    pass
