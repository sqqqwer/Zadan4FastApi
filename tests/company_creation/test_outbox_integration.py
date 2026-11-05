from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.models.company import Company
from auth.models.outbox_messages import OutboxMessagesAuth
from shared.events.kafka_adapters import KafkaEventProducer
from shared.outbox.publisher import OutboxPublisher
from tests.events.constants import PUBLICATION_ATTEMPTS_AFTER_RECOVERY


@pytest.mark.parametrize("company_registration_data", ["valid"], indirect=True)
async def test_registration_survives_kafka_failure(
    get_async_client,
    company_registration_data,
    test_db,
    monkeypatch,
):
    """HTTP registration commits its company and event even while Kafka cannot accept sends."""
    send = AsyncMock(side_effect=TimeoutError("Kafka unavailable"))
    monkeypatch.setattr(KafkaEventProducer, "publish", send)

    response = await get_async_client.post(
        "/auth/api/v1/sign-up-complete",
        json=company_registration_data,
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert response.status_code == status.HTTP_201_CREATED, response.text
    company_id = UUID(response.json()["company_id"])
    assert await test_db.get(Company, company_id) is not None
    message = await test_db.scalar(select(OutboxMessagesAuth).where(OutboxMessagesAuth.aggregate_id == company_id))
    assert message is not None and message.published_at is None
    assert message.event_type == "company.created"
    send.assert_not_awaited()
    await test_db.commit()
    factory = async_sessionmaker(test_db.bind, expire_on_commit=False, join_transaction_mode="create_savepoint")
    producer = AsyncMock(spec=KafkaEventProducer)
    producer.publish = send
    publisher = OutboxPublisher(producer, OutboxMessagesAuth, factory)

    await publisher.publish_batch()

    await test_db.refresh(message)
    assert message.published_at is None
    assert message.attempts == 1
    assert "Kafka unavailable" in message.last_error
    await test_db.commit()
    send.side_effect = None

    await publisher.publish_batch()

    await test_db.refresh(message)
    assert message.published_at is not None
    assert message.last_error is None
    assert message.attempts == PUBLICATION_ATTEMPTS_AFTER_RECOVERY
    assert send.await_args.args[0].event_id == message.event_id
