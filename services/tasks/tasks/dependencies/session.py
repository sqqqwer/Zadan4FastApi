from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.uow.session_scope import session_scope

from ..database import async_session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a session from this service's database."""
    async with session_scope(async_session_factory) as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session, scope="function")]
