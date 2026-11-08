import asyncio
from functools import partial

from httpx import AsyncClient

from shared.events.bus import KafkaEventsBus
from shared.events.kafka_adapters import KafkaEventConsumer
from shared.inbox.repository import InboxSqlAlchemyRepository
from shared.logging.config import setup_logging

from .config import get_settings
from .database import async_engine, async_session_factory
from .dependencies.statistics import get_heartbeat_reporter
from .events import subscribe_handlers
from .models.inbox_messages import InboxMessagesOrg


async def main() -> None:
    """Run the org event consumer and close its resources on exit."""
    setup_logging()
    settings = get_settings()
    bus = KafkaEventsBus(kafka_bootstrap_servers=settings.kafka_bootstrap_servers)
    await subscribe_handlers(bus)

    try:
        async with AsyncClient(timeout=settings.heartbeat_timeout_seconds) as client:
            heartbeat = get_heartbeat_reporter(client, "consumer")
            consumer = KafkaEventConsumer(
                bus=bus,
                inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesOrg),
                consumer_name="tasks-platform.org",
                kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
                session_factory=async_session_factory,
                topics=("auth.events", "org.events", "tasks.events", "saga.events"),
                heartbeat=heartbeat,
            )
            async with bus.producer.producer, consumer.consumer, heartbeat.running():
                await consumer.run()
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
