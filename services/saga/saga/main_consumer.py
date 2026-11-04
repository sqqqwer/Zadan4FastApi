import asyncio
import logging
from functools import partial

from sqlalchemy.exc import SQLAlchemyError

from shared.events.bus import KafkaEventsBus
from shared.events.kafka_adapters import KafkaEventConsumer
from shared.inbox.repository import InboxSqlAlchemyRepository
from shared.logging.config import setup_logging

from .config import Settings, get_settings
from .database import async_engine, async_session_factory
from .dependencies.services import get_saga_service
from .dependencies.session import get_session
from .events import subscribe_handlers
from .models.inbox_messages import InboxMessagesSaga
from .services.constants import CONSUMER_NAME

logger = logging.getLogger(__name__)


async def monitor_timeouts(settings: Settings) -> None:
    """Report stalled steps even while the consumer is waiting for new messages."""
    while True:
        try:
            async with get_session() as session:
                await get_saga_service(session).log_stalled(settings.saga_step_timeout_seconds)
        except SQLAlchemyError:
            logger.exception("Saga timeout check failed")
        await asyncio.sleep(settings.saga_timeout_check_interval_seconds)


async def main() -> None:
    """Run the onboarding consumer and timeout monitor without an HTTP application."""
    setup_logging()
    settings = get_settings()
    bus = KafkaEventsBus(kafka_bootstrap_servers=settings.kafka_bootstrap_servers)
    await subscribe_handlers(bus)
    consumer = KafkaEventConsumer(
        bus=bus,
        inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesSaga),
        consumer_name=CONSUMER_NAME,
        kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
        session_factory=async_session_factory,
    )

    try:
        async with bus.producer.producer, consumer.consumer, asyncio.TaskGroup() as tasks:
            tasks.create_task(consumer.run())
            tasks.create_task(monitor_timeouts(settings))
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
