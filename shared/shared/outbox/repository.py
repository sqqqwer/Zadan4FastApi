from abc import ABC, abstractmethod
from typing import override

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.base.models.models import BaseModelWithoutId
from shared.events.envelope import EventEnvelope


class OutboxAbstractRepository(ABC):
    """Abstract repository for outgoing events."""

    @abstractmethod
    async def add(self, envelope: EventEnvelope, dedup_key: str) -> None:
        """Add an outgoing event to the current business transaction.

        Args:
            envelope: Event data and metadata.
            dedup_key: Deterministic key identifying the business event.
        """
        ...

    @abstractmethod
    async def add_once(self, envelope: EventEnvelope, dedup_key: str) -> None:
        """Enqueue a business result unless the same result is already in the outbox."""
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

    @override
    async def add_once(self, envelope: EventEnvelope, dedup_key: str) -> None:
        envelope_data = envelope.model_dump(mode="json")
        statement = (
            insert(self.model)
            .values(
                event_id=envelope.event_id,
                event_type=envelope.event_type.value,
                aggregate_id=envelope.aggregate_id,
                dedup_key=dedup_key,
                payload=envelope_data["payload"],
                envelope=envelope_data,
            )
            .on_conflict_do_nothing(index_elements=["dedup_key"])
        )
        await self.session.execute(statement)
