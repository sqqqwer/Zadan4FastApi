from abc import ABC, abstractmethod
from typing import override

from sqlalchemy.ext.asyncio import AsyncSession


class UowAbstract(ABC):
    """Abstract unit of work."""

    @abstractmethod
    async def flush(self) -> None:
        """Flush pending database changes."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Commit the database transaction."""
        ...


class UowSqlAlchemy(UowAbstract):
    """Unit of work using a SQLAlchemy session."""

    def __init__(self, session: AsyncSession):
        """Initialize the unit of work.

        Args:
            session: Database session used by the unit of work.
        """
        self.session = session

    @override
    async def flush(self) -> None:
        await self.session.flush()

    @override
    async def commit(self) -> None:
        await self.session.commit()
