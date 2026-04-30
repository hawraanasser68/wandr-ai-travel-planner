"""
Alembic async env — required for SQLAlchemy 2.x async engines.
Reads DATABASE_URL from the same .env file as the app so there's one source of truth.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Import Base and all models so Alembic sees the metadata
from app.db.session import Base
from app.models import db as _models  # noqa: F401 — import triggers registration
from app.config import get_settings

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic what schema looks like so it can generate diffs
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run without a live DB connection (generates SQL scripts)."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run against a live DB using the async engine."""
    connectable = create_async_engine(settings.database_url)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
