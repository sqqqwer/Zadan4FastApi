import asyncio

from httpx import AsyncClient

from shared.events.kafka_adapters import KafkaEventProducer
from shared.logging.config import setup_logging
from shared.outbox.publisher import OutboxPublisher

from .config import get_settings
from .database import async_engine, async_session_factory
from .dependencies.statistics import get_heartbeat_reporter
from .models.outbox_messages import OutboxMessagesOrg


async def main() -> None:
    """Run the org outbox publisher and close its resources on exit."""
    setup_logging()
    settings = get_settings()
    producer = KafkaEventProducer(kafka_bootstrap_servers=settings.kafka_bootstrap_servers)

    try:
        async with AsyncClient(timeout=settings.heartbeat_timeout_seconds) as client:
            heartbeat = get_heartbeat_reporter(client, "publisher")
            publisher = OutboxPublisher(
                producer=producer,
                model=OutboxMessagesOrg,
                session_factory=async_session_factory,
                heartbeat=heartbeat,
            )
            async with producer.producer, heartbeat.running():
                await publisher.run()
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
