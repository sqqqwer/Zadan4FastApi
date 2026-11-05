import json
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from aiokafka import TopicPartition
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.events import kafka_adapters
from shared.events.envelope import EventEnvelope
from shared.events.exceptions import TransientEventError
from shared.events.types import EventType
from tasks.events import on_create_welcome_task_handler, save_user_replica
from tasks.models.inbox_messages import InboxMessagesTasks
from tasks.models.task import Task
from tasks.models.users_replica import UsersReplicaTasks

from . import constants


async def test_duplicate_event_has_one_business_effect(consumer, envelope, make_message, test_db):
    """A replay skips the handler and keeps exactly one welcome task and inbox receipt."""
    saga_id = uuid4()
    envelope = envelope.model_copy(
        update={
            "event_type": EventType.TASKS_CREATE_WELCOME_TASK,
            "producer": "saga",
            "aggregate_id": saga_id,
            "payload": {
                "saga_id": str(saga_id),
                "user_id": str(uuid4()),
                "company_id": str(uuid4()),
                "invite_id": str(uuid4()),
                "position_id": str(uuid4()),
                "struct_id": str(uuid4()),
            },
        }
    )
    handler = AsyncMock(wraps=on_create_welcome_task_handler)
    await consumer.bus.subscribe(envelope.event_type, handler)
    raw = envelope.model_dump_json().encode()
    consumer.consumer.messages = [make_message(raw), make_message(raw, 1)]

    await consumer.run()

    handler.assert_awaited_once()
    assert (
        await test_db.scalar(
            select(func.count()).select_from(Task).where(Task.responsible_id == UUID(envelope.payload["user_id"]))
        )
        == 1
    )
    assert (
        await test_db.scalar(
            select(func.count())
            .select_from(InboxMessagesTasks)
            .where(InboxMessagesTasks.consumer_name == "tests.tasks", InboxMessagesTasks.event_id == envelope.event_id)
        )
        == 1
    )
    assert consumer.consumer.commit.await_args_list[1].args == ({TopicPartition("auth.events", 0): 2},)


async def test_handler_failure_rolls_back_inbox_and_effect(consumer, envelope, make_message, test_db):
    """A failed handler leaves no receipt or replica, so redelivery can succeed."""

    async def fail_after_write(event, session):
        await save_user_replica(event, session)
        await session.flush()
        raise RuntimeError("handler failed after flush")

    await consumer.bus.subscribe(envelope.event_type, fail_after_write)
    consumer.consumer.messages = [make_message(envelope.model_dump_json().encode())]

    with pytest.raises(RuntimeError, match="after flush"):
        await consumer.run()

    assert await test_db.get(UsersReplicaTasks, envelope.aggregate_id) is None
    assert await test_db.get(InboxMessagesTasks, ("tests.tasks", envelope.event_id)) is None
    consumer.consumer.commit.assert_not_awaited()
    consumer.bus.event_handlers[envelope.event_type] = [save_user_replica]
    await consumer.run()
    assert await test_db.get(UsersReplicaTasks, envelope.aggregate_id) is not None
    assert await test_db.get(InboxMessagesTasks, ("tests.tasks", envelope.event_id)) is not None


async def test_database_commit_precedes_offset(consumer, envelope, make_message, test_db):
    """Offset acknowledgement observes a completed transaction with its business effect."""
    sessions = []

    async def handler(event, session):
        sessions.append(session)
        await save_user_replica(event, session)

    async def commit_offset(offsets):
        assert not sessions[0].in_transaction()
        assert await test_db.get(UsersReplicaTasks, envelope.aggregate_id) is not None
        assert await test_db.get(InboxMessagesTasks, ("tests.tasks", envelope.event_id)) is not None
        assert offsets == {TopicPartition("auth.events", 0): 1}

    await consumer.bus.subscribe(envelope.event_type, handler)
    consumer.consumer.commit.side_effect = commit_offset
    consumer.consumer.messages = [make_message(envelope.model_dump_json().encode())]

    await consumer.run()

    consumer.consumer.commit.assert_awaited_once()


@pytest.mark.parametrize("invalid_kind", ["json", "event_type", "payload"])
async def test_fatal_message_goes_to_dlq_and_next_message_runs(  # noqa: PLR0913, PLR0917
    consumer,
    envelope,
    make_message,
    mock_producer,
    test_db,
    invalid_kind,
):
    """Poison messages preserve their bytes and do not block a following valid event."""
    invalid = envelope.model_dump(mode="json")
    if invalid_kind == "json":
        raw = b"{broken-json"
    elif invalid_kind == "event_type":
        invalid["event_type"] = "unknown.event"
        raw = json.dumps(invalid).encode()
    else:
        invalid["payload"] = {}
        raw = json.dumps(invalid).encode()
    handler = AsyncMock(wraps=save_user_replica)
    await consumer.bus.subscribe(envelope.event_type, handler)
    consumer.consumer.messages = [make_message(raw), make_message(envelope.model_dump_json().encode(), 1)]

    await consumer.run()

    mock_producer.producer.send_and_wait.assert_awaited_once()
    kwargs = mock_producer.producer.send_and_wait.await_args.kwargs
    letter = json.loads(kwargs["value"])
    assert kwargs["topic"] == "auth.events.dlq"
    assert kwargs["key"] == b"user"
    assert letter["original_message"] == raw.decode()
    assert letter["source_topic"] == "auth.events"
    assert letter["partition"] == 0 and letter["offset"] == 0
    assert letter["reason"] and letter["error_type"]
    assert letter["attempts"] == 1
    assert await test_db.get(UsersReplicaTasks, envelope.aggregate_id) is not None
    assert consumer.consumer.commit.await_count == len(consumer.consumer.messages)


async def test_dlq_failure_does_not_commit_offset(consumer, envelope, make_message, mock_producer):
    """A failed DLQ delivery cannot acknowledge the poisoned source message."""
    mock_producer.producer.send_and_wait.side_effect = OSError("DLQ unavailable")
    consumer.consumer.messages = [make_message(b"broken")]

    with pytest.raises(OSError, match="DLQ unavailable"):
        await consumer.run()

    consumer.consumer.commit.assert_not_awaited()


@pytest.mark.parametrize("recover", [True, False])
async def test_transient_errors_retry_with_backoff(  # noqa: PLR0913, PLR0917
    consumer,
    envelope,
    make_message,
    mock_producer,
    monkeypatch,
    test_db,
    recover,
):
    """Transient failures roll back before retry and eventually succeed or reach DLQ."""
    delays = AsyncMock()
    monkeypatch.setattr(kafka_adapters.asyncio, "sleep", delays)
    attempts = 0

    async def handler(event: EventEnvelope, session: AsyncSession):
        nonlocal attempts
        attempts += 1
        await save_user_replica(event, session)
        await session.flush()
        if not recover or attempts < constants.RECOVERY_ATTEMPT:
            raise TransientEventError("temporary database failure")

    await consumer.bus.subscribe(envelope.event_type, handler)
    consumer.consumer.messages = [make_message(envelope.model_dump_json().encode())]

    await consumer.run()

    assert [call.args[0] for call in delays.await_args_list] == ([1, 2] if recover else [1, 2, 4, 8])
    assert attempts == (constants.RECOVERY_ATTEMPT if recover else constants.MAX_EXPECTED_ATTEMPTS)
    assert (await test_db.get(UsersReplicaTasks, envelope.aggregate_id) is not None) is recover
    assert (await test_db.get(InboxMessagesTasks, ("tests.tasks", envelope.event_id)) is not None) is recover
    if recover:
        mock_producer.producer.send_and_wait.assert_not_awaited()
    else:
        letter = json.loads(mock_producer.producer.send_and_wait.await_args.kwargs["value"])
        assert letter["attempts"] == constants.MAX_EXPECTED_ATTEMPTS
        assert "temporary database failure" in letter["reason"]
    consumer.consumer.commit.assert_awaited_once()
