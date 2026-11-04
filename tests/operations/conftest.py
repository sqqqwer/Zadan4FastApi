import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.structs import OffsetAndMetadata
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import auth.dependencies.session as auth_session_dependencies
import org.dependencies.session as org_session_dependencies
import saga.dependencies.session as saga_session_dependencies
import tasks.dependencies.session as tasks_session_dependencies
from shared.operations import service as operations
from shared.operations.schemas import PendingOutboxMessage

from . import constants


@pytest.fixture(params=["auth", "org", "tasks", "saga"])
def service_name(request: pytest.FixtureRequest) -> str:
    """Select each HTTP service for operational endpoint tests.

    Args:
        request: Pytest request containing the selected service.

    Returns:
        str: Service name used by the shared application fixture.
    """
    return request.param


@pytest.fixture
def mock_session(monkeypatch: pytest.MonkeyPatch, service_name: str) -> AsyncMock:
    """Replace the database session created by the service's get_session.

    Args:
        monkeypatch: Pytest helper for temporary patches.
        service_name: Service whose session factory is replaced.

    Returns:
        AsyncMock: Database session with commit and rollback tracking.
    """
    session = AsyncMock(spec=AsyncSession)
    session.in_transaction.return_value = True

    def clear_transaction() -> None:
        session.in_transaction.return_value = False

    session.rollback.side_effect = clear_transaction
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = session
    session_dependencies = {
        "auth": auth_session_dependencies,
        "org": org_session_dependencies,
        "tasks": tasks_session_dependencies,
        "saga": saga_session_dependencies,
    }[service_name]
    monkeypatch.setattr(session_dependencies, "async_session_factory", session_factory)
    return session


@pytest.fixture
def mock_kafka_client(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Replace the Kafka client used by readiness checks.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        AsyncMock: Kafka admin client.
    """
    client = AsyncMock(spec=AIOKafkaAdminClient)
    monkeypatch.setattr(operations, "AIOKafkaAdminClient", MagicMock(return_value=client))
    return client


@pytest.fixture
def mock_kafka_reader(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Replace the Kafka client used to inspect partition offsets.

    Args:
        monkeypatch: Pytest helper for temporary patches.

    Returns:
        AsyncMock: Kafka reader without group membership.
    """
    reader = AsyncMock(spec=AIOKafkaConsumer)
    monkeypatch.setattr(operations, "AIOKafkaConsumer", MagicMock(return_value=reader))
    return reader


@pytest.fixture
async def get_async_client(
    service_app: FastAPI,
    mock_session: AsyncMock,
    mock_kafka_client: AsyncMock,
    mock_kafka_reader: AsyncMock,
) -> AsyncIterator[AsyncClient]:
    """Get an HTTP client with mocked database and Kafka connections.

    Args:
        service_app: Application selected for the current service.
        mock_session: Database session supplied through get_session.
        mock_kafka_client: Kafka client used by readiness checks.
        mock_kafka_reader: Kafka reader used by consumer lag checks.

    Yields:
        AsyncClient: HTTP client for sending requests to the application.
    """
    transport = ASGITransport(app=service_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def database_state(request: pytest.FixtureRequest, mock_session: AsyncMock) -> None:
    """Prepare an available or unavailable database connection.

    Args:
        request: Pytest request containing the selected database state.
        mock_session: Database session used by the test.
    """
    if request.param == "unavailable":
        mock_session.execute.side_effect = OSError("Database unavailable")


@pytest.fixture
def kafka_state(request: pytest.FixtureRequest, mock_kafka_client: AsyncMock) -> None:
    """Prepare an available or unavailable Kafka connection.

    Args:
        request: Pytest request containing the selected Kafka state.
        mock_kafka_client: Kafka client used by the test.
    """
    if request.param == "unavailable":
        mock_kafka_client.start.side_effect = OSError("Kafka unavailable")


@pytest.fixture
def timeout_dependency(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    mock_session: AsyncMock,
    mock_kafka_client: AsyncMock,
) -> str:
    """Make the selected dependency stall beyond the readiness timeout.

    Args:
        request: Pytest request containing the selected dependency.
        monkeypatch: Pytest helper for temporary patches.
        mock_session: Database session used by the test.
        mock_kafka_client: Kafka client used by the test.

    Returns:
        str: Name of the dependency expected to time out.
    """
    monkeypatch.setattr(operations, "READINESS_TIMEOUT_SECONDS", 0.01)

    async def stall(*args, **kwargs):
        await asyncio.Event().wait()

    operation = mock_session.execute if request.param == "database" else mock_kafka_client.describe_cluster
    operation.side_effect = stall
    return request.param


@pytest.fixture
def pending_outbox_message() -> PendingOutboxMessage:
    """Create publication diagnostics for an unsent event.

    Returns:
        PendingOutboxMessage: Expected outbox message data.
    """
    return PendingOutboxMessage(
        id=1,
        event_id=constants.EVENT_ID,
        event_type=constants.EVENT_TYPE,
        correlation_id=constants.CORRELATION_ID,
        created_at=constants.CREATED_AT,
        attempts=constants.ATTEMPTS,
        last_error=constants.LAST_ERROR,
    )


@pytest.fixture
def outbox_state(
    request: pytest.FixtureRequest,
    mock_session: AsyncMock,
    pending_outbox_message: PendingOutboxMessage,
) -> None:
    """Prepare a page of pending messages or an empty outbox.

    Args:
        request: Pytest request containing the selected outbox state.
        mock_session: Database session used by the test.
        pending_outbox_message: Message returned for a populated outbox.
    """
    has_messages = request.param == "valid"
    mock_session.scalar.return_value = constants.OUTBOX_TOTAL if has_messages else 0
    result = MagicMock()
    result.mappings.return_value = [pending_outbox_message.model_dump()] if has_messages else []
    mock_session.execute.return_value = result


@pytest.fixture
def consumer_lag_state(
    request: pytest.FixtureRequest,
    mock_kafka_client: AsyncMock,
    mock_kafka_reader: AsyncMock,
) -> None:
    """Prepare partition offsets for a consumer group lag scenario.

    Args:
        request: Pytest request containing the selected offset state.
        mock_kafka_client: Admin client supplying committed offsets.
        mock_kafka_reader: Reader supplying partition metadata and available offsets.
    """
    offsets = constants.PARTITION_OFFSETS
    beginnings = {partition: values[0] for partition, values in offsets.items()}
    ends = {partition: values[1] for partition, values in offsets.items()}
    commits = {partition: OffsetAndMetadata(values[2], "") for partition, values in offsets.items()}
    if request.param == "caught_up":
        commits = {partition: OffsetAndMetadata(end, "") for partition, end in ends.items()}
    elif request.param == "no_commits":
        commits = {}
    elif request.param == "negative_commits":
        commits = {partition: OffsetAndMetadata(-1, "") for partition in offsets}
    elif request.param == "zero_commits":
        beginnings = dict.fromkeys(offsets, 0)
        commits = {partition: OffsetAndMetadata(0, "") for partition in offsets}
    elif request.param == "expired_commits":
        commits = {partition: OffsetAndMetadata(beginning - 1, "") for partition, beginning in beginnings.items()}

    def partitions_for_topic(topic: str) -> set[int]:
        if request.param == "no_topics":
            return set()
        return {partition.partition for partition in offsets if partition.topic == topic}

    mock_kafka_reader.partitions_for_topic.side_effect = partitions_for_topic
    mock_kafka_reader.beginning_offsets.return_value = beginnings
    mock_kafka_reader.end_offsets.return_value = ends
    mock_kafka_client.list_consumer_group_offsets.return_value = commits


@pytest.fixture
def consumer_lag_failure(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    mock_kafka_client: AsyncMock,
    mock_kafka_reader: AsyncMock,
) -> None:
    """Fail the Kafka startup or offset lookup, or exceed the probe timeout.

    Args:
        request: Pytest request containing the selected failure.
        monkeypatch: Pytest helper for temporary patches.
        mock_kafka_client: Admin client used by the test.
        mock_kafka_reader: Reader used by the test.
    """
    mock_kafka_reader.partitions_for_topic.return_value = {0}
    if request.param == "unavailable":
        mock_kafka_client.start.side_effect = OSError("Kafka unavailable")
    elif request.param == "offset_error":
        mock_kafka_reader.end_offsets.side_effect = OSError("Offsets unavailable")
    elif request.param == "timeout":
        monkeypatch.setattr(operations, "READINESS_TIMEOUT_SECONDS", 0.01)

        async def stall(*args, **kwargs):
            await asyncio.Event().wait()

        mock_kafka_reader.end_offsets.side_effect = stall
