import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import URL
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.resources.exceptions import ConflictError

from .config import get_settings

logger = logging.getLogger(__name__)


DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",
    username=get_settings().postgres_user,
    password=get_settings().postgres_password.get_secret_value(),
    host=get_settings().db_host,
    port=get_settings().db_port,
    database=get_settings().postgres_db,
)

async_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession]:
    """Manage a database session and commit or roll back its transaction.

    Yields:
        AsyncSession: Database session for the current operation.

    Raises:
        ConflictError: If a unique or foreign key constraint is violated.
    """
    try:
        async with async_session_factory() as session:
            try:
                yield session
                if session.in_transaction():
                    await session.commit()
            except Exception:
                await session.rollback()
                raise
    except IntegrityError as error:
        error_code = getattr(error.orig, "sqlstate", None)
        if error_code in ("23505", "23503"):
            raise ConflictError() from error
        logger.error(f"DB integrity error: code={error_code}")
        raise
    except DBAPIError as error:
        error_code = getattr(error.orig, "sqlstate", None)
        logger.error(f"DB driver error: code={error_code}")
        raise
