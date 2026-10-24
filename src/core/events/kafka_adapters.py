from typing import TYPE_CHECKING

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition

from src.core.config import get_settings
from src.core.database import session_scope
from src.core.request_context import correlation_id_var

from .envelope import EventEnvelope

if TYPE_CHECKING:
    from .bus import KafkaEventsBus


class KafkaEventProducer:
    """Event producer using Kafka."""

    def __init__(self) -> None:
        """Initialize the Kafka producer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=get_settings().kafka_bootstrap_servers
        )

    async def publish(self, envelope: EventEnvelope) -> None:
        """Publish an event to its producer's topic.

        Args:
            envelope: Event data and metadata.
        """
        await self.producer.send_and_wait(
            topic=f"{envelope.producer}.events",
            key=str(envelope.aggregate_id).encode("utf-8"),
            value=envelope.model_dump_json().encode("utf-8"),
        )

class KafkaEventConsumer:
    """Event consumer using Kafka."""

    def __init__(self, bus: "KafkaEventsBus") -> None:
        """Initialize the Kafka consumer.

        Args:
            bus: Event bus used to dispatch received events.
        """
        self.bus = bus
        self.consumer = AIOKafkaConsumer(
            "auth.events",
            "org.events",
            "tasks.events",
            bootstrap_servers=get_settings().kafka_bootstrap_servers,
            group_id="tasks-platform",
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )

    async def run(self) -> None:
        """Consume events and commit offsets after successful processing."""
        async for message in self.consumer:
            envelope = EventEnvelope.model_validate_json(message.value)
            correlation_token = correlation_id_var.set(str(envelope.correlation_id))

            try:
                async with session_scope():
                    await self.bus.dispatch(envelope)

                partition = TopicPartition(message.topic, message.partition)
                await self.consumer.commit(
                    {partition: message.offset + 1}
                )
            finally:
                correlation_id_var.reset(correlation_token)
