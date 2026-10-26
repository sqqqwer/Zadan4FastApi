from abc import abstractmethod
from typing import override
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repositories.base import BaseRepository

from .model_mixin import InboxMessagesMixin


class InboxAbstractRepository(BaseRepository):
    """Abstract repository for processed incoming events."""

    @abstractmethod
    async def try_register(self, consumer_name: str, event_id: UUID) -> bool:
        """Insert a receipt in the current business transaction without committing.

        Args:
            consumer_name: Stable name of the event consumer.
            event_id: UUID of the incoming event.

        Returns:
            bool: True if inserted, False if this consumer already processed the event.
        """
        ...


class InboxSqlAlchemyRepository(InboxAbstractRepository):
    """SQLAlchemy repository for processed incoming events."""

    def __init__(self, session: AsyncSession, model: type[InboxMessagesMixin]) -> None:
        """Initialize the repository.

        Args:
            session: Database session shared with the business repositories and unit of work.
            model: Inbox database model of the current module.
        """
        self.session = session
        self.model = model

    @override
    async def try_register(self, consumer_name: str, event_id: UUID) -> bool:
        statement = (
            insert(self.model)
            .values(consumer_name=consumer_name, event_id=event_id)
            .on_conflict_do_nothing(index_elements=[self.model.consumer_name, self.model.event_id])
            .returning(self.model.event_id)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None
