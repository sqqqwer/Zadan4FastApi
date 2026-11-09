import asyncio
from contextlib import nullcontext

from httpx import AsyncClient

from shared.events.kafka_adapters import KafkaEventProducer
from shared.logging.config import setup_logging
from shared.outbox.publisher import OutboxPublisher
from shared.tracing.instrumentation import instrument_databases

from .config import get_settings
from .database import async_engine, async_session_factory
from .dependencies.statistics import get_heartbeat_reporter
from .dependencies.tracing import get_tracing_reporter
from .models.outbox_messages import OutboxMessagesSaga


async def main() -> None:
    """Publish persisted onboarding commands to saga.events."""
    setup_logging()
    settings = get_settings()
    tracing = get_tracing_reporter()
    async with tracing.running() if tracing is not None else nullcontext():
        try:
            if tracing is not None:
                instrument_databases([async_engine], tracing)
            producer = KafkaEventProducer(kafka_bootstrap_servers=settings.kafka_bootstrap_servers, tracing=tracing)
            async with AsyncClient(timeout=settings.heartbeat_timeout_seconds) as client:
                heartbeat = get_heartbeat_reporter(client, "publisher")
                publisher = OutboxPublisher(
                    producer=producer,
                    model=OutboxMessagesSaga,
                    session_factory=async_session_factory,
                    heartbeat=heartbeat,
                    tracing=tracing,
                )
                async with producer.producer, heartbeat.running():
                    await publisher.run()
        finally:
            await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
