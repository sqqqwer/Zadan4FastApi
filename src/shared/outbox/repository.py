from abc import abstractmethod
from typing import override

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.events.envelope import EventEnvelope
from src.core.models.base import BaseModelWithoutId
from src.core.repositories.base import BaseRepository


class OutboxAbstractRepository(BaseRepository):
    """Abstract repository for outgoing events."""

    @abstractmethod
    async def add(self, envelope: EventEnvelope, dedup_key: str) -> None:
        """Add an outgoing event to the current business transaction.

        Args:
            envelope: Event data and metadata.
            dedup_key: Deterministic key identifying the business event.
        """
        ...


class OutboxSqlAlchemyRepository(OutboxAbstractRepository):
    """SQLAlchemy repository for outgoing events."""

    def __init__(self, session: AsyncSession, model: type[BaseModelWithoutId]):
        """Initialize the repository.

        Args:
            session: Database session shared with the business repositories and unit of work.
            model: Outbox database model of the current module.
        """
        self.session = session
        self.model = model

    @override
    async def add(self, envelope: EventEnvelope, dedup_key: str) -> None:
        """Add an outgoing event without flushing or committing the transaction.

        Args:
            envelope: Event data and metadata.
            dedup_key: Deterministic key identifying the business event.
        """
        envelope_data = envelope.model_dump(mode="json")
        outbox_message = self.model(
            event_id=envelope.event_id,
            event_type=envelope.event_type.value,
            aggregate_id=envelope.aggregate_id,
            dedup_key=dedup_key,
            payload=envelope_data["payload"],
            envelope=envelope_data,
        )
        self.session.add(outbox_message)
