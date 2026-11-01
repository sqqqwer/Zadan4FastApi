import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.resources.exceptions import ConflictError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def session_scope(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
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
