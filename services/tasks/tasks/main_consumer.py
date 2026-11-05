import asyncio
from functools import partial

from shared.events.bus import KafkaEventsBus
from shared.events.kafka_adapters import KafkaEventConsumer
from shared.events.types import EventType
from shared.inbox.repository import InboxSqlAlchemyRepository
from shared.logging.config import setup_logging

from .config import get_settings
from .database import async_engine, async_session_factory
from .events import subscribe_handlers
from .models.inbox_messages import InboxMessagesTasks
from .resources.constants import USER_SNAPSHOT_V2


async def main() -> None:
    """Run the tasks event consumer and close its resources on exit."""
    setup_logging()
    settings = get_settings()
    bus = KafkaEventsBus(kafka_bootstrap_servers=settings.kafka_bootstrap_servers)
    await subscribe_handlers(bus)
    consumer = KafkaEventConsumer(
        bus=bus,
        inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesTasks),
        consumer_name="tasks-platform.tasks",
        kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
        session_factory=async_session_factory,
        topics=("auth.events", "org.events", "tasks.events", "saga.events"),
        supported_schema_versions={
            EventType.COMPANY_CREATED: (1, USER_SNAPSHOT_V2),
            EventType.EMPLOYEE_CREATED: (1, USER_SNAPSHOT_V2),
        },
    )

    try:
        async with bus.producer.producer, consumer.consumer:
            await consumer.run()
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
