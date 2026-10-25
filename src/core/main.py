from asyncio import TaskGroup
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.events.bus import KafkaEventsBus
from src.core.events.kafka_adapters import KafkaEventConsumer
from src.core.logging.config import setup_logging
from src.core.resources.exceptions_handler import exception_handlers
from src.modules.auth.api.v1.auth import router as auth_router
from src.modules.auth.events import subscribe_handlers as auth_subscribe_handlers
from src.modules.auth.models.outbox_messages import OutboxMessagesAuth
from src.modules.org.api.v1.org import router as org_router
from src.modules.org.events import subscribe_handlers as org_subscribe_handlers
from src.modules.org.models.outbox_messages import OutboxMessagesOrg
from src.modules.tasks.api.v1.tasks import router as tasks_router
from src.modules.tasks.events import subscribe_handlers as tasks_subscribe_handlers
from src.modules.tasks.models.outbox_messages import OutboxMessagesTasks
from src.shared.outbox.publisher import OutboxPublisher

from .middleware import correlation_id_middleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Set up event handlers and run the Kafka consumer and outbox publishers.

    Cancel background tasks and close Kafka connections on shutdown.

    Args:
        app: FastAPI application.

    Yields:
        None: Control while the application is running.
    """
    bus = KafkaEventsBus()
    consumer = KafkaEventConsumer(bus=bus)
    producer = bus.producer.producer

    await auth_subscribe_handlers(bus)
    await org_subscribe_handlers(bus)
    await tasks_subscribe_handlers(bus)

    publishers = [
        OutboxPublisher(bus.producer, OutboxMessagesAuth),
        OutboxPublisher(bus.producer, OutboxMessagesOrg),
        OutboxPublisher(bus.producer, OutboxMessagesTasks),
    ]

    async with producer, consumer.consumer, TaskGroup() as tasks:
        consumer_task = tasks.create_task(consumer.run())

        publisher_tasks = [tasks.create_task(publisher.run()) for publisher in publishers]

        try:
            yield
        finally:
            consumer_task.cancel()
            for task in publisher_tasks:
                task.cancel()


setup_logging()

app = FastAPI(
    exception_handlers=exception_handlers,
    lifespan=lifespan,
)

app.middleware("http")(correlation_id_middleware)

app.include_router(auth_router)
app.include_router(org_router)
app.include_router(tasks_router)
