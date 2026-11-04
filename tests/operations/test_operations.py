import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from shared.operations import service as operations
from shared.operations.schemas import ConsumerLagResponse, PendingOutboxMessage, PendingOutboxResponse

from . import constants


async def test_service_health(
    get_async_client: AsyncClient,
    service_app: FastAPI,
    mock_session: AsyncMock,
    mock_kafka_client: AsyncMock,
):
    """Check HTTP liveness without accessing the database or Kafka.

    Args:
        get_async_client: Async HTTP client for the test application.
        service_app: Application selected for the current service.
        mock_session: Mock database session.
        mock_kafka_client: Mock Kafka client.
    """
    response = await get_async_client.get("/health")

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Correlation-ID"]
    assert {"/health", "/ready", "/outbox", "/consumer-lag"} <= service_app.openapi()["paths"].keys()
    mock_session.execute.assert_not_awaited()
    mock_kafka_client.start.assert_not_awaited()


@pytest.mark.parametrize(
    argnames=["database_state", "kafka_state", "expected_response", "expected_status_code"],
    argvalues=[
        ("available", "available", {"status": "ready", "database": "ok", "kafka": "ok"}, status.HTTP_200_OK),
        (
            "unavailable",
            "available",
            {"status": "not_ready", "database": "error", "kafka": "ok"},
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ),
        (
            "available",
            "unavailable",
            {"status": "not_ready", "database": "ok", "kafka": "error"},
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ),
        (
            "unavailable",
            "unavailable",
            {"status": "not_ready", "database": "error", "kafka": "error"},
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ),
    ],
    indirect=["database_state", "kafka_state"],
)
async def test_readiness(  # noqa: PLR0913, PLR0917
    get_async_client: AsyncClient,
    mock_session: AsyncMock,
    mock_kafka_client: AsyncMock,
    database_state: None,
    kafka_state: None,
    expected_response: dict[str, str],
    expected_status_code: int,
):
    """Check readiness with different database and Kafka states.

    Args:
        get_async_client: Async HTTP client for the test application.
        mock_session: Mock database session.
        mock_kafka_client: Mock Kafka client.
        database_state: Prepared database availability.
        kafka_state: Prepared Kafka availability.
        expected_response: Expected dependency status data.
        expected_status_code: Expected HTTP status code.
    """
    response = await get_async_client.get("/ready")

    assert response.status_code == expected_status_code, response.text
    assert response.json() == expected_response
    mock_kafka_client.close.assert_awaited_once()
    if expected_response["database"] == "error":
        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_awaited()
    else:
        mock_session.commit.assert_awaited_once()


@pytest.mark.parametrize(
    argnames=["timeout_dependency"],
    argvalues=[("database",), ("kafka",)],
    indirect=["timeout_dependency"],
)
async def test_readiness_timeout(
    get_async_client: AsyncClient,
    mock_session: AsyncMock,
    mock_kafka_client: AsyncMock,
    timeout_dependency: str,
):
    """Check that a stalled dependency produces a 503 response.

    Args:
        get_async_client: Async HTTP client for the test application.
        mock_session: Mock database session.
        mock_kafka_client: Mock Kafka client.
        timeout_dependency: Dependency prepared to exceed the readiness timeout.
    """
    response = await asyncio.wait_for(get_async_client.get("/ready"), timeout=1)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE, response.text
    assert response.json()[timeout_dependency] == "error"
    mock_kafka_client.close.assert_awaited_once()
    if timeout_dependency == "database":
        mock_session.rollback.assert_awaited_once()


@pytest.mark.parametrize(
    argnames=["outbox_state", "expected_total", "expected_count"],
    argvalues=[
        ("valid", constants.OUTBOX_TOTAL, 1),
        ("empty", 0, 0),
    ],
    indirect=["outbox_state"],
)
async def test_outbox(  # noqa: PLR0913, PLR0917
    get_async_client: AsyncClient,
    outbox_state: None,
    pending_outbox_message: PendingOutboxMessage,
    caplog: pytest.LogCaptureFixture,
    expected_total: int,
    expected_count: int,
):
    """Check the pending count, message data and outbox log entry.

    Args:
        get_async_client: Async HTTP client for the test application.
        outbox_state: Prepared pending messages or an empty outbox.
        pending_outbox_message: Expected publication diagnostics.
        caplog: Pytest helper for capturing log messages.
        expected_total: Expected total number of pending messages.
        expected_count: Expected number of messages on the requested page.
    """
    with caplog.at_level("INFO", logger=operations.__name__):
        response = await get_async_client.get("/outbox", params={"page": 2, "size": 20})

    assert response.status_code == status.HTTP_200_OK, response.text
    data = PendingOutboxResponse.model_validate(response.json())
    assert data.total == expected_total
    assert len(data.items) == expected_count
    if expected_count:
        assert data.items[0] == pending_outbox_message
        assert "payload" not in response.json()["items"][0]
    assert f"Outbox pending: count={expected_total}" in caplog.text


async def test_outbox_invalid_pagination(get_async_client: AsyncClient):
    """Check that the endpoint rejects a page size above the allowed limit.

    Args:
        get_async_client: Async HTTP client for the test application.
    """
    response = await get_async_client.get("/outbox", params={"size": 101})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, response.text


@pytest.mark.parametrize(
    argnames=["consumer_lag_state", "expected_lags"],
    argvalues=[
        ("valid", (10, 20, 0)),
        ("caught_up", (0, 0, 0)),
        ("no_commits", (80, 80, 45)),
        ("negative_commits", (80, 80, 45)),
        ("zero_commits", (100, 80, 50)),
        ("expired_commits", (80, 80, 45)),
        ("no_topics", ()),
    ],
    indirect=["consumer_lag_state"],
)
async def test_consumer_lag(  # noqa: PLR0913, PLR0917
    get_async_client: AsyncClient,
    service_name: str,
    consumer_lag_state: None,
    mock_kafka_client: AsyncMock,
    mock_kafka_reader: AsyncMock,
    expected_lags: tuple[int, ...],
    caplog: pytest.LogCaptureFixture,
):
    """Check lag calculation for existing, missing and expired committed offsets.

    Args:
        get_async_client: Async HTTP client for the test application.
        service_name: Service whose consumer group is measured.
        consumer_lag_state: Prepared partition and group offsets.
        mock_kafka_client: Admin client supplying group offsets.
        mock_kafka_reader: Reader supplying available offsets.
        expected_lags: Expected lag of each partition in response order.
        caplog: Pytest helper for capturing log messages.
    """
    with caplog.at_level("INFO", logger=operations.__name__):
        response = await get_async_client.get("/consumer-lag")

    assert response.status_code == status.HTTP_200_OK, response.text
    data = ConsumerLagResponse.model_validate(response.json())
    assert data.status == "ok"
    assert data.group_id == f"tasks-platform.{service_name}"
    assert data.total_lag == sum(expected_lags)
    assert tuple(partition.lag for partition in data.partitions) == expected_lags
    if expected_lags:
        assert [(partition.topic, partition.partition) for partition in data.partitions] == list(
            constants.PARTITION_OFFSETS
        )
        mock_kafka_client.list_consumer_group_offsets.assert_awaited_once_with(
            data.group_id, partitions=list(constants.PARTITION_OFFSETS)
        )
        for partition in data.partitions:
            assert partition.committed_offset is None or partition.committed_offset >= 0
    else:
        mock_kafka_client.list_consumer_group_offsets.assert_not_awaited()
    assert f"Consumer lag: group_id={data.group_id} total_lag={data.total_lag}" in caplog.text
    assert operations.AIOKafkaConsumer.call_args.kwargs["group_id"] is None
    assert operations.AIOKafkaConsumer.call_args.kwargs["enable_auto_commit"] is False
    mock_kafka_reader.commit.assert_not_awaited()
    mock_kafka_reader.subscribe.assert_not_called()
    mock_kafka_client.close.assert_awaited_once()
    mock_kafka_reader.stop.assert_awaited_once()


@pytest.mark.parametrize(
    argnames=["consumer_lag_failure"],
    argvalues=[("unavailable",), ("offset_error",), ("timeout",)],
    indirect=["consumer_lag_failure"],
)
async def test_consumer_lag_unavailable(
    get_async_client: AsyncClient,
    service_name: str,
    consumer_lag_failure: None,
    mock_kafka_client: AsyncMock,
    mock_kafka_reader: AsyncMock,
):
    """Check that Kafka failures return 503 without reporting a zero lag.

    Args:
        get_async_client: Async HTTP client for the test application.
        service_name: Service whose consumer group is measured.
        consumer_lag_failure: Prepared Kafka error or timeout.
        mock_kafka_client: Admin client used by the test.
        mock_kafka_reader: Reader used by the test.
    """
    response = await asyncio.wait_for(get_async_client.get("/consumer-lag"), timeout=1)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE, response.text
    assert response.json() == {
        "status": "error",
        "group_id": f"tasks-platform.{service_name}",
        "total_lag": None,
        "partitions": [],
    }
    mock_kafka_client.close.assert_awaited_once()
    mock_kafka_reader.stop.assert_awaited_once()
