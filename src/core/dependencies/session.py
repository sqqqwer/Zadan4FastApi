import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import session_scope

logger = logging.getLogger(__name__)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Get a database session for the current request.

    Yields:
        AsyncSession: Database session managed by session_scope().
    """
    async with session_scope() as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session, scope="function")]
