from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import override

from sqlalchemy.ext.asyncio import AsyncSession

from .envelope import EventEnvelope
from .kafka_adapters import KafkaEventProducer
from .types import EventType

EventHandler = Callable[[EventEnvelope, AsyncSession], Awaitable[None]]


class AbstractEventsBus(ABC):
    """Abstract event bus."""

    @abstractmethod
    async def publish(self, envelope: EventEnvelope) -> None:
        """Publish an event to its handlers.

        Args:
            envelope: Event data and metadata.
        """
        ...

    @abstractmethod
    async def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Event type handled by the handler.
            handler: Async handler called for this event type.
        """
        ...


class InMemoryEventBus(AbstractEventsBus):
    """Event bus with handlers stored in memory."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the event bus."""
        self.session = session
        self.event_handlers: dict[EventType, list[EventHandler]] = {}

    @override
    async def publish(self, envelope: EventEnvelope) -> None:
        for handler in self.event_handlers.get(envelope.event_type, []):
            await handler(envelope, self.session)

    @override
    async def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self.event_handlers.setdefault(event_type, []).append(handler)


class KafkaEventsBus(AbstractEventsBus):
    """Event bus using Kafka."""

    def __init__(self, producer: KafkaEventProducer | None = None) -> None:
        """Initialize the event bus with an optional shared producer."""
        self.producer = producer if producer is not None else KafkaEventProducer()
        self.event_handlers: dict[EventType, list[EventHandler]] = {}

    @override
    async def publish(self, envelope: EventEnvelope) -> None:
        await self.producer.publish(envelope=envelope)

    @override
    async def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self.event_handlers.setdefault(event_type, []).append(handler)

    async def dispatch(self, envelope: EventEnvelope, session: AsyncSession) -> None:
        """Call registered handlers for the event type.

        Args:
            envelope: Event data and metadata.
            session: Database session shared by all handlers and the inbox.
        """
        for handler in self.event_handlers.get(envelope.event_type, []):
            await handler(envelope, session)
