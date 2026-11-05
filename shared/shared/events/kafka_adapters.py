import asyncio
import json
import logging
from base64 import b64encode
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition
from aiokafka.structs import ConsumerRecord
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.correlation.request_context import correlation_id_var
from shared.inbox.repository import InboxAbstractRepository
from shared.resources.exceptions import DomainValidationError
from shared.uow.session_scope import session_scope

from .dlq import DeadLetterMessage
from .envelope import EventEnvelope
from .exceptions import FatalEventError, is_transient_error
from .types import EventType

logger = logging.getLogger(__name__)

MAX_PROCESSING_ATTEMPTS = 5
RETRY_BACKOFF_SECONDS = 1

if TYPE_CHECKING:
    from .bus import KafkaEventsBus


class KafkaEventProducer:
    """Event producer using Kafka."""

    def __init__(self, kafka_bootstrap_servers: str) -> None:
        """Initialize the Kafka producer.

        Args:
            kafka_bootstrap_servers: Kafka broker addresses supplied by the service.
        """
        self.producer = AIOKafkaProducer(bootstrap_servers=kafka_bootstrap_servers)

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

    def __init__(  # noqa: PLR0913
        self,
        bus: "KafkaEventsBus",
        inbox_factory: Callable[[AsyncSession], InboxAbstractRepository],
        consumer_name: str,
        kafka_bootstrap_servers: str,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        topics: tuple[str, ...] = ("auth.events", "org.events", "tasks.events"),
        supported_schema_versions: dict[EventType, tuple[int, ...]] | None = None,
    ) -> None:
        """Initialize the Kafka consumer.

        Args:
            bus: Event bus used to dispatch received events.
            inbox_factory: Create an inbox repository bound to the current message's session.
            consumer_name: Stable module consumer name, also used as the Kafka group ID.
            kafka_bootstrap_servers: Kafka broker addresses supplied by the service.
            session_factory: Factory for sessions in the service's own database.
            topics: Topics needed by this consumer, including command topics for saga participants.
            supported_schema_versions: Accepted versions by event type; other events accept only version 1.
        """
        self.bus = bus
        self.inbox_factory = inbox_factory
        self.consumer_name = consumer_name
        self.session_factory = session_factory
        self.supported_schema_versions = supported_schema_versions or {}

        self.consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=kafka_bootstrap_servers,
            group_id=consumer_name,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )

    async def run(self) -> None:
        """Commit offsets only after processing or confirmed delivery to the DLQ."""
        async for message in self.consumer:
            correlation_token = correlation_id_var.set("-")
            try:
                await self._process_message(message)
                partition = TopicPartition(message.topic, message.partition)
                await self.consumer.commit({partition: message.offset + 1})
            finally:
                correlation_id_var.reset(correlation_token)

    async def _process_message(self, message: ConsumerRecord[bytes, bytes]) -> None:
        envelope: EventEnvelope | None = None
        for attempt in range(1, MAX_PROCESSING_ATTEMPTS + 1):
            try:
                if envelope is None:
                    if message.value is None:
                        raise FatalEventError("Event message must not be null")
                    envelope = EventEnvelope.model_validate_json(message.value)
                    correlation_id_var.set(str(envelope.correlation_id))
                    supported_versions = self.supported_schema_versions.get(envelope.event_type, (1,))
                    if envelope.schema_version not in supported_versions:
                        raise FatalEventError(f"Unsupported schema_version={envelope.schema_version}")
                async with session_scope(self.session_factory) as session:
                    inbox = self.inbox_factory(session)
                    if await inbox.try_register(consumer_name=self.consumer_name, event_id=envelope.event_id):
                        await self.bus.dispatch(envelope, session)
                return
            except (ValueError, KeyError, DomainValidationError) as error:
                await self._send_to_dlq(message, error, attempt, envelope)
                return
            except Exception as error:
                if not is_transient_error(error):
                    logger.exception(
                        "Unexpected event processing error: topic=%s partition=%s offset=%s attempt=%s",
                        message.topic,
                        message.partition,
                        message.offset,
                        attempt,
                    )
                    raise
                if attempt == MAX_PROCESSING_ATTEMPTS:
                    await self._send_to_dlq(message, error, attempt, envelope)
                    return
                delay = RETRY_BACKOFF_SECONDS * 2 ** (attempt - 1)
                logger.warning(
                    "Event retry: topic=%s partition=%s offset=%s attempt=%s/%s delay_seconds=%s reason=%s: %s",
                    message.topic,
                    message.partition,
                    message.offset,
                    attempt,
                    MAX_PROCESSING_ATTEMPTS,
                    delay,
                    type(error).__name__,
                    error,
                )
                await asyncio.sleep(delay)

    async def _send_to_dlq(
        self,
        message: ConsumerRecord[bytes, bytes],
        error: Exception,
        attempts: int,
        envelope: EventEnvelope | None,
    ) -> None:
        if envelope is None:
            try:
                payload = json.loads(message.value or b"null")
                correlation_id = UUID(payload["correlation_id"])
            except (ValueError, KeyError, TypeError, AttributeError):
                pass
            else:
                correlation_id_var.set(str(correlation_id))

        encoding: Literal["utf-8", "base64"] = "utf-8"
        original_message = None
        if message.value is not None:
            try:
                original_message = message.value.decode("utf-8")
            except UnicodeDecodeError:
                original_message = b64encode(message.value).decode("ascii")
                encoding = "base64"
        letter = DeadLetterMessage(
            source_topic=message.topic,
            partition=message.partition,
            offset=message.offset,
            consumer_name=self.consumer_name,
            original_message=original_message,
            original_encoding=encoding,
            reason=str(error),
            error_type=type(error).__name__,
            attempts=attempts,
            correlation_id=UUID(correlation_id_var.get()) if correlation_id_var.get() != "-" else None,
            failed_at=datetime.now(UTC),
        )
        topic = f"{message.topic}.dlq"
        try:
            await self.bus.producer.producer.send_and_wait(
                topic=topic,
                key=message.key,
                value=letter.model_dump_json().encode("utf-8"),
                headers=list(message.headers),
            )
        except Exception:
            logger.exception(
                "DLQ delivery failed; offset not committed: topic=%s partition=%s offset=%s",
                message.topic,
                message.partition,
                message.offset,
            )
            raise
        logger.error(
            "Event sent to DLQ: topic=%s source_topic=%s partition=%s offset=%s attempts=%s reason=%s: %s",
            topic,
            message.topic,
            message.partition,
            message.offset,
            attempts,
            type(error).__name__,
            error,
        )
