import asyncio
import logging
from datetime import UTC, datetime

from aiokafka.errors import KafkaError
from sqlalchemy import select

from src.core.database import session_scope
from src.core.events.envelope import EventEnvelope
from src.core.events.kafka_adapters import KafkaEventProducer
from src.shared.outbox.model_mixin import OutboxMessagesMixin

logger = logging.getLogger(__name__)


class OutboxPublisher:
    """Publisher for outgoing events stored in a module's outbox."""

    def __init__(
        self,
        producer: KafkaEventProducer,
        model: type[OutboxMessagesMixin],
    ) -> None:
        """Initialize the outbox publisher.

        Args:
            producer: Kafka producer used to publish outgoing events.
            model: Outbox database model of the current module.
        """
        self.producer = producer
        self.model = model

    async def publish_batch(self) -> None:
        """Publish a locked batch of outgoing events and save publication results."""
        async with session_scope() as session:
            statement = (
                select(self.model)
                .where(self.model.published_at.is_(None))
                .order_by(self.model.id)
                .limit(100)
                .with_for_update(skip_locked=True)
            )

            messages = (await session.scalars(statement)).all()

            for message in messages:
                envelope = EventEnvelope.model_validate(message.envelope)
                message.attempts += 1

                try:
                    async with asyncio.timeout(10):
                        await self.producer.publish(envelope)
                except (KafkaError, TimeoutError) as error:
                    message.last_error = f"{type(error).__name__}: {error}"
                    logger.warning(f"Outbox publish failed: event_id={message.event_id}, error={message.last_error}")
                    break
                else:
                    message.published_at = datetime.now(UTC)
                    message.last_error = None
                    logger.info(
                        f"Outbox event published to Kafka: event_type={message.event_type}, "
                        f"event_id={message.event_id}, topic={envelope.producer}.events"
                    )

    async def run(self) -> None:
        """Poll the outbox and retry publication after failed iterations."""
        while True:
            try:
                await self.publish_batch()
            except Exception:
                logger.exception("Outbox publisher iteration failed")

            await asyncio.sleep(0.5)
