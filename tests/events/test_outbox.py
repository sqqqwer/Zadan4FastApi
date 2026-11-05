import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.outbox.publisher import OutboxPublisher
from shared.outbox.repository import OutboxSqlAlchemyRepository
from shared.resources.exceptions import ConflictError
from shared.uow.session_scope import session_scope
from tasks.models.outbox_messages import OutboxMessagesTasks
from tasks.models.users_replica import UsersReplicaTasks

from . import constants


async def test_outbox_and_business_change_roll_back_together(event_session_factory, envelope, test_db):
    """An aborted business transaction cannot leave either a replica or an outgoing event."""
    with pytest.raises(RuntimeError, match="business failed"):
        async with session_scope(event_session_factory) as session:
            session.add(
                UsersReplicaTasks(
                    id=envelope.aggregate_id,
                    company_id=uuid4(),
                    full_name="Rollback User",
                    is_active=True,
                    last_event_at=datetime.now(UTC),
                )
            )
            await OutboxSqlAlchemyRepository(session, OutboxMessagesTasks).add(envelope, str(envelope.event_id))
            await session.flush()
            raise RuntimeError("business failed")

    assert await test_db.get(UsersReplicaTasks, envelope.aggregate_id) is None
    assert (
        await test_db.scalar(select(OutboxMessagesTasks).where(OutboxMessagesTasks.event_id == envelope.event_id))
        is None
    )


async def test_dedup_key_prevents_second_outbox_event(event_session_factory, envelope, test_db):
    """A deterministic business key rejects a different event ID for the same result."""
    dedup_key = f"employee.created:{envelope.aggregate_id}"
    async with session_scope(event_session_factory) as session:
        await OutboxSqlAlchemyRepository(session, OutboxMessagesTasks).add(envelope, dedup_key)
    duplicate = envelope.model_copy(update={"event_id": uuid4()})
    with pytest.raises(ConflictError):
        async with session_scope(event_session_factory) as session:
            await OutboxSqlAlchemyRepository(session, OutboxMessagesTasks).add(duplicate, dedup_key)
    async with session_scope(event_session_factory) as session:
        await OutboxSqlAlchemyRepository(session, OutboxMessagesTasks).add_once(duplicate, dedup_key)

    rows = (await test_db.scalars(select(OutboxMessagesTasks).where(OutboxMessagesTasks.dedup_key == dedup_key))).all()
    assert len(rows) == 1
    assert rows[0].event_id == envelope.event_id


async def test_publish_failure_preserves_pending_event(event_session_factory, envelope, mock_producer, test_db):
    """The same stored event is retried after Kafka recovers, without regenerating its ID."""
    async with session_scope(event_session_factory) as session:
        await OutboxSqlAlchemyRepository(session, OutboxMessagesTasks).add(envelope, str(envelope.event_id))
    publisher = OutboxPublisher(mock_producer, OutboxMessagesTasks, event_session_factory)
    mock_producer.publish.side_effect = TimeoutError("Kafka unavailable")

    await publisher.publish_batch()

    message = await test_db.scalar(
        select(OutboxMessagesTasks).where(OutboxMessagesTasks.event_id == envelope.event_id)
    )
    assert message.published_at is None
    assert message.attempts == 1
    assert "Kafka unavailable" in message.last_error
    await test_db.commit()
    mock_producer.publish.side_effect = None

    await publisher.publish_batch()

    await test_db.refresh(message)
    assert message.published_at is not None
    assert message.attempts == constants.PUBLICATION_ATTEMPTS_AFTER_RECOVERY
    assert message.last_error is None
    assert [call.args[0].event_id for call in mock_producer.publish.await_args_list] == [envelope.event_id] * 2


async def test_publishers_skip_locked_rows_and_keep_id_order(database_url, envelope):
    """Two independent PostgreSQL connections cannot publish the same locked batch."""
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    events = [envelope.model_copy(update={"event_id": uuid4()}) for _ in range(3)]
    event_ids = [event.event_id for event in events]
    acquired = asyncio.Event()
    release = asyncio.Event()
    sent = []
    first_task = None

    async def publish(event):
        sent.append(event.event_id)
        acquired.set()
        await release.wait()

    try:
        async with session_scope(factory) as session:
            repository = OutboxSqlAlchemyRepository(session, OutboxMessagesTasks)
            for event in events:
                await repository.add(event, str(event.event_id))
        async with engine.connect() as first, engine.connect() as second, factory() as unrelated:
            # Keep any pre-existing test data outside both publishers' batches.
            await unrelated.execute(
                select(OutboxMessagesTasks)
                .where(
                    OutboxMessagesTasks.event_id.not_in(event_ids),
                    OutboxMessagesTasks.published_at.is_(None),
                )
                .with_for_update()
            )
            first_publisher = OutboxPublisher(
                AsyncMock(publish=AsyncMock(side_effect=publish)),
                OutboxMessagesTasks,
                async_sessionmaker(first, expire_on_commit=False),
            )
            second_producer = AsyncMock()
            second_publisher = OutboxPublisher(
                second_producer, OutboxMessagesTasks, async_sessionmaker(second, expire_on_commit=False)
            )
            first_task = asyncio.create_task(first_publisher.publish_batch())
            await asyncio.wait_for(acquired.wait(), timeout=5)
            await asyncio.wait_for(second_publisher.publish_batch(), timeout=5)
            second_producer.publish.assert_not_awaited()
            release.set()
            await asyncio.wait_for(first_task, timeout=5)
        async with factory() as session:
            rows = (
                await session.scalars(
                    select(OutboxMessagesTasks)
                    .where(OutboxMessagesTasks.event_id.in_(event_ids))
                    .order_by(OutboxMessagesTasks.id)
                )
            ).all()
            assert sent == [row.event_id for row in rows] == event_ids
            assert all(row.published_at is not None and row.attempts == 1 for row in rows)
    finally:
        release.set()
        if first_task is not None and not first_task.done():
            first_task.cancel()
            await asyncio.gather(first_task, return_exceptions=True)
        async with session_scope(factory) as session:
            await session.execute(delete(OutboxMessagesTasks).where(OutboxMessagesTasks.event_id.in_(event_ids)))
        await engine.dispose()
