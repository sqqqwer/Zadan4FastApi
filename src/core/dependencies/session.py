import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory
from src.core.resources.exceptions import ConflictError

logger = logging.getLogger(__name__)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Get a database session and commit or roll back the transaction.

    Yields:
        AsyncSession: Database session for the current operation.

    Raises:
        ConflictError: If the operation conflicts with existing data.
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


SessionDependency = Annotated[AsyncSession, Depends(get_session, scope="function")]
