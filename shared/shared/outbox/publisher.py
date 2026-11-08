import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from aiokafka.errors import KafkaError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.correlation.request_context import correlation_id_var
from shared.events.envelope import EventEnvelope
from shared.events.kafka_adapters import KafkaEventProducer
from shared.outbox.model_mixin import OutboxMessagesMixin
from shared.uow.session_scope import session_scope

if TYPE_CHECKING:
    from shared.statistics.abstracts import ProgressAbstractReporter

logger = logging.getLogger(__name__)


class OutboxPublisher:
    """Publisher for outgoing events stored in a module's outbox."""

    def __init__(
        self,
        producer: KafkaEventProducer,
        model: type[OutboxMessagesMixin],
        session_factory: async_sessionmaker[AsyncSession],
        *,
        heartbeat: "ProgressAbstractReporter | None" = None,
    ) -> None:
        """Initialize the outbox publisher.

        Args:
            producer: Kafka producer used to publish outgoing events.
            model: Outbox database model of the current module.
            session_factory: Factory for sessions in the service's own database.
            heartbeat: Optional observer of database polling and publication progress.
        """
        self.producer = producer
        self.model = model
        self.session_factory = session_factory
        self.heartbeat = heartbeat

    async def publish_batch(self) -> None:
        """Publish a locked batch of outgoing events and save publication results."""
        async with session_scope(self.session_factory) as session:
            statement = (
                select(self.model)
                .where(self.model.published_at.is_(None))
                .order_by(self.model.id)
                .limit(100)
                .with_for_update(skip_locked=True)
            )

            messages = (await session.scalars(statement)).all()
            if self.heartbeat is not None:
                self.heartbeat.mark_progress()

            for message in messages:
                envelope = EventEnvelope.model_validate(message.envelope)
                message.attempts += 1
                correlation_token = correlation_id_var.set(str(envelope.correlation_id))

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
                    if self.heartbeat is not None:
                        self.heartbeat.mark_progress()
                    logger.info(
                        f"Outbox event published to Kafka: event_type={message.event_type}, "
                        f"event_id={message.event_id}, topic={envelope.producer}.events"
                    )
                finally:
                    correlation_id_var.reset(correlation_token)

        if self.heartbeat is not None:
            self.heartbeat.mark_progress()

    async def run(self) -> None:
        """Poll the outbox and retry publication after failed iterations."""
        while True:
            try:
                await self.publish_batch()
            except Exception:
                logger.exception("Outbox publisher iteration failed")

            await asyncio.sleep(0.5)
