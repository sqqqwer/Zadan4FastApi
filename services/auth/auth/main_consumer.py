import asyncio
from functools import partial

from shared.events.bus import KafkaEventsBus
from shared.events.kafka_adapters import KafkaEventConsumer
from shared.inbox.repository import InboxSqlAlchemyRepository
from shared.logging.config import setup_logging

from .config import get_settings
from .database import async_engine, async_session_factory
from .events import subscribe_handlers
from .models.inbox_messages import InboxMessagesAuth


async def main() -> None:
    """Run the auth event consumer and close its resources on exit."""
    setup_logging()
    settings = get_settings()
    bus = KafkaEventsBus(kafka_bootstrap_servers=settings.kafka_bootstrap_servers)
    await subscribe_handlers(bus)
    consumer = KafkaEventConsumer(
        bus=bus,
        inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesAuth),
        consumer_name="tasks-platform.auth",
        kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
        session_factory=async_session_factory,
    )

    try:
        async with bus.producer.producer, consumer.consumer:
            await consumer.run()
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
