import asyncio
import logging
from contextlib import nullcontext
from functools import partial

from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from shared.events.bus import KafkaEventsBus
from shared.events.exceptions import is_transient_error
from shared.events.kafka_adapters import KafkaEventConsumer, KafkaEventProducer
from shared.inbox.repository import InboxSqlAlchemyRepository
from shared.logging.config import setup_logging
from shared.tracing.instrumentation import instrument_databases

from .config import Settings, get_settings
from .database import async_engine, async_session_factory
from .dependencies.services import get_saga_service
from .dependencies.session import get_session
from .dependencies.statistics import get_heartbeat_reporter
from .dependencies.tracing import get_tracing_reporter
from .events import subscribe_handlers
from .models.inbox_messages import InboxMessagesSaga
from .services.constants import CONSUMER_NAME

logger = logging.getLogger(__name__)


async def monitor_timeouts(settings: Settings) -> None:
    """Report stalled steps even while the consumer is waiting for new messages."""
    tracing = get_tracing_reporter()
    while True:
        try:
            with tracing.span("saga.check_timeouts") if tracing is not None else nullcontext():
                async with get_session() as session:
                    await get_saga_service(session).log_stalled(settings.saga_step_timeout_seconds)
        except Exception as error:
            if not isinstance(error, SQLAlchemyError) and not is_transient_error(error):
                raise
            logger.exception("Saga timeout check failed")
        await asyncio.sleep(settings.saga_timeout_check_interval_seconds)


async def main() -> None:
    """Run the onboarding consumer and timeout monitor without an HTTP application."""
    setup_logging()
    settings = get_settings()
    tracing = get_tracing_reporter()
    async with tracing.running() if tracing is not None else nullcontext():
        try:
            if tracing is not None:
                instrument_databases([async_engine], tracing)
            producer = KafkaEventProducer(kafka_bootstrap_servers=settings.kafka_bootstrap_servers, tracing=tracing)
            bus = KafkaEventsBus(kafka_bootstrap_servers=settings.kafka_bootstrap_servers, producer=producer)
            await subscribe_handlers(bus)
            async with AsyncClient(timeout=settings.heartbeat_timeout_seconds) as client:
                heartbeat = get_heartbeat_reporter(client, "consumer")
                consumer = KafkaEventConsumer(
                    bus=bus,
                    inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesSaga),
                    consumer_name=CONSUMER_NAME,
                    kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
                    session_factory=async_session_factory,
                    heartbeat=heartbeat,
                    tracing=tracing,
                )
                async with (
                    bus.producer.producer,
                    consumer.consumer,
                    heartbeat.running(),
                    asyncio.TaskGroup() as tasks,
                ):
                    tasks.create_task(consumer.run())
                    tasks.create_task(monitor_timeouts(settings))
        finally:
            await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
