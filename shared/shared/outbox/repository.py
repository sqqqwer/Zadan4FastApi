from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, override

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.base.models.models import BaseModelWithoutId
from shared.events.envelope import EventEnvelope

if TYPE_CHECKING:
    from shared.tracing.abstracts import TracingAbstractReporter


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

    def __init__(
        self,
        session: AsyncSession,
        model: type[BaseModelWithoutId],
        *,
        tracing: "TracingAbstractReporter | None" = None,
    ):
        """Initialize the repository.

        Args:
            session: Database session shared with the business repositories and unit of work.
            model: Outbox database model of the current module.
            tracing: Optional provider of context stored alongside the event.
        """
        self.session = session
        self.model = model
        self.tracing = tracing

    def _serialize_envelope(self, envelope: EventEnvelope) -> dict[str, Any]:
        """Persist context in existing JSON metadata without changing the event schema."""
        data = envelope.model_dump(mode="json")
        if self.tracing is not None:
            carrier = self.tracing.inject_context()
            if carrier:
                data["trace_context"] = carrier
        return data

    @override
    async def add(self, envelope: EventEnvelope, dedup_key: str) -> None:
        """Add an outgoing event without flushing or committing the transaction.

        Args:
            envelope: Event data and metadata.
            dedup_key: Deterministic key identifying the business event.
        """
        envelope_data = self._serialize_envelope(envelope)
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
        envelope_data = self._serialize_envelope(envelope)
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
