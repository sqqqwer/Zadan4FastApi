import asyncio
from contextlib import nullcontext
from functools import partial

from httpx import AsyncClient

from shared.events.bus import KafkaEventsBus
from shared.events.kafka_adapters import KafkaEventConsumer, KafkaEventProducer
from shared.inbox.repository import InboxSqlAlchemyRepository
from shared.logging.config import setup_logging
from shared.tracing.instrumentation import instrument_databases

from .config import get_settings
from .database import async_engine, async_session_factory
from .dependencies.statistics import get_heartbeat_reporter
from .dependencies.tracing import get_tracing_reporter
from .events import subscribe_handlers
from .models.inbox_messages import InboxMessagesOrg


async def main() -> None:
    """Run the org event consumer and close its resources on exit."""
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
                    inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesOrg),
                    consumer_name="tasks-platform.org",
                    kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
                    session_factory=async_session_factory,
                    topics=("auth.events", "org.events", "tasks.events", "saga.events"),
                    heartbeat=heartbeat,
                    tracing=tracing,
                )
                async with bus.producer.producer, consumer.consumer, heartbeat.running():
                    await consumer.run()
        finally:
            await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
