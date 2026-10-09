from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import override

from .envelope import EventEnvelope
from .types import EventType

EventHandler = Callable[[EventEnvelope], Awaitable[None]]


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

    def __init__(self) -> None:
        """Initialize the event bus."""
        self.event_handlers: dict[EventType, list[EventHandler]] = {}

    @override
    async def publish(self, envelope: EventEnvelope) -> None:
        for handler in self.event_handlers.get(envelope.event_type, []):
            await handler(envelope)

    @override
    async def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self.event_handlers.setdefault(event_type, []).append(handler)
