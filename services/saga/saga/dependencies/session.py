from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from shared.uow.session_scope import session_scope

from ..database import async_session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Open one local transaction for a background operation."""
    async with session_scope(async_session_factory) as session:
        yield session
