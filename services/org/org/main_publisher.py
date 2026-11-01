import asyncio

from shared.events.kafka_adapters import KafkaEventProducer
from shared.logging.config import setup_logging
from shared.outbox.publisher import OutboxPublisher

from .config import get_settings
from .database import async_engine, async_session_factory
from .models.outbox_messages import OutboxMessagesOrg


async def main() -> None:
    """Run the org outbox publisher and close its resources on exit."""
    setup_logging()
    settings = get_settings()
    producer = KafkaEventProducer(kafka_bootstrap_servers=settings.kafka_bootstrap_servers)
    publisher = OutboxPublisher(
        producer=producer,
        model=OutboxMessagesOrg,
        session_factory=async_session_factory,
    )

    try:
        async with producer.producer:
            await publisher.run()
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
