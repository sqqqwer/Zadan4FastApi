from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from functools import partial
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from aiokafka.structs import ConsumerRecord
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.correlation.request_context import correlation_id_var
from shared.events import kafka_adapters
from shared.events.bus import KafkaEventsBus
from shared.events.envelope import EventEnvelope
from shared.events.kafka_adapters import KafkaEventConsumer, KafkaEventProducer
from shared.events.types import EventType
from shared.inbox.repository import InboxSqlAlchemyRepository
from tasks.models.inbox_messages import InboxMessagesTasks

from .stubs import StubKafkaReader


@pytest.fixture
def service_name() -> str:
    """Use tasks PostgreSQL for event integration tests."""
    return "tasks"


@pytest.fixture(autouse=True)
def correlation_context() -> Iterator[None]:
    """Restore correlation context even when processing fails."""
    token = correlation_id_var.set(str(uuid4()))
    try:
        yield
    finally:
        correlation_id_var.reset(token)


@pytest.fixture
def envelope() -> EventEnvelope:
    """Build a valid auth user snapshot."""
    user_id = uuid4()
    return EventEnvelope(
        event_id=uuid4(),
        event_type=EventType.EMPLOYEE_CREATED,
        aggregate_id=user_id,
        occurred_at=datetime.now(UTC),
        correlation_id=uuid4(),
        producer="auth",
        payload={"user_id": str(user_id), "company_id": str(uuid4()), "full_name": "Test User", "is_active": True},
    )


@pytest.fixture
def make_message() -> Callable[..., ConsumerRecord]:
    """Wrap serialized bytes in the same record consumed from aiokafka."""

    def create(value: bytes, offset: int = 0) -> ConsumerRecord:
        return ConsumerRecord(
            topic="auth.events",
            partition=0,
            offset=offset,
            timestamp=0,
            timestamp_type=0,
            key=b"user",
            value=value,
            checksum=None,
            serialized_key_size=4,
            serialized_value_size=len(value),
            headers=(),
        )

    return create


@pytest.fixture
def mock_producer() -> MagicMock:
    """Replace only the Kafka transport, keeping database work real."""
    producer = MagicMock(spec=KafkaEventProducer)
    producer.publish = AsyncMock()
    producer.producer = MagicMock()
    producer.producer.send_and_wait = AsyncMock()
    return producer


@pytest.fixture
def event_session_factory(test_db: AsyncSession) -> async_sessionmaker[AsyncSession]:
    """Give each message its own savepoint in the test transaction."""
    return async_sessionmaker(bind=test_db.bind, expire_on_commit=False, join_transaction_mode="create_savepoint")


@pytest.fixture
def consumer(
    monkeypatch: pytest.MonkeyPatch,
    event_session_factory: async_sessionmaker[AsyncSession],
    mock_producer: MagicMock,
) -> KafkaEventConsumer:
    """Use the production consumer with a finite reader and real PostgreSQL inbox."""
    monkeypatch.setattr(kafka_adapters, "AIOKafkaConsumer", lambda *args, **kwargs: StubKafkaReader())
    bus = KafkaEventsBus("unused:9092", producer=mock_producer)
    return KafkaEventConsumer(
        bus=bus,
        inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesTasks),
        consumer_name="tests.tasks",
        kafka_bootstrap_servers="unused:9092",
        session_factory=event_session_factory,
        supported_schema_versions={EventType.EMPLOYEE_CREATED: (1, 2)},
    )
