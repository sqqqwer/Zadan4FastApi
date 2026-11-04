from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.uow.session_scope import session_scope

from ..database import async_session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Open one local transaction for a background operation."""
    async with session_scope(async_session_factory) as session:
        yield session


async def get_http_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield the saga session through FastAPI while retaining background usage."""
    async with get_session() as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_http_session, scope="function")]
