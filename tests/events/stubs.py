from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

from aiokafka.structs import ConsumerRecord


class StubKafkaReader:
    """Deliver a finite batch without starting a Kafka connection."""

    def __init__(self) -> None:
        """Keep messages and offset acknowledgements visible to the test."""
        self.messages: list[ConsumerRecord] = []
        self.commit = AsyncMock()

    def __aiter__(self) -> AsyncIterator[ConsumerRecord]:
        """Iterate once over the prepared messages."""
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[ConsumerRecord]:
        for message in self.messages:
            yield message
