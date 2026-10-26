from asyncio import TaskGroup
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from functools import partial

from fastapi import FastAPI

from src.core.events.bus import KafkaEventsBus
from src.core.events.kafka_adapters import KafkaEventConsumer, KafkaEventProducer
from src.core.logging.config import setup_logging
from src.core.resources.exceptions_handler import exception_handlers
from src.modules.auth.api.v1.auth import router as auth_router
from src.modules.auth.events import subscribe_handlers as auth_subscribe_handlers
from src.modules.auth.models.inbox_messages import InboxMessagesAuth
from src.modules.auth.models.outbox_messages import OutboxMessagesAuth
from src.modules.org.api.v1.org import router as org_router
from src.modules.org.events import subscribe_handlers as org_subscribe_handlers
from src.modules.org.models.inbox_messages import InboxMessagesOrg
from src.modules.org.models.outbox_messages import OutboxMessagesOrg
from src.modules.tasks.api.v1.tasks import router as tasks_router
from src.modules.tasks.events import subscribe_handlers as tasks_subscribe_handlers
from src.modules.tasks.models.inbox_messages import InboxMessagesTasks
from src.modules.tasks.models.outbox_messages import OutboxMessagesTasks
from src.shared.inbox.repository import InboxSqlAlchemyRepository
from src.shared.outbox.publisher import OutboxPublisher

from .middleware import correlation_id_middleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Set up module event handlers, Kafka consumers, and outbox publishers.

    Cancel background tasks and close Kafka connections on shutdown.

    Args:
        app: FastAPI application.

    Yields:
        None: Control while the application is running.
    """
    producer = KafkaEventProducer()
    auth_bus = KafkaEventsBus(producer)
    org_bus = KafkaEventsBus(producer)
    tasks_bus = KafkaEventsBus(producer)

    await auth_subscribe_handlers(auth_bus)
    await org_subscribe_handlers(org_bus)
    await tasks_subscribe_handlers(tasks_bus)

    publishers = [
        OutboxPublisher(producer, OutboxMessagesAuth),
        OutboxPublisher(producer, OutboxMessagesOrg),
        OutboxPublisher(producer, OutboxMessagesTasks),
    ]
    consumers = [
        KafkaEventConsumer(
            bus=auth_bus,
            inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesAuth),
            consumer_name="tasks-platform.auth",
        ),
        KafkaEventConsumer(
            bus=org_bus,
            inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesOrg),
            consumer_name="tasks-platform.org",
        ),
        KafkaEventConsumer(
            bus=tasks_bus,
            inbox_factory=partial(InboxSqlAlchemyRepository, model=InboxMessagesTasks),
            consumer_name="tasks-platform.tasks",
        ),
    ]

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(producer.producer)
        for consumer in consumers:
            await stack.enter_async_context(consumer.consumer)

        async with TaskGroup() as tasks:
            consumer_tasks = [tasks.create_task(consumer.run()) for consumer in consumers]
            publisher_tasks = [tasks.create_task(publisher.run()) for publisher in publishers]

            try:
                yield
            finally:
                for task in consumer_tasks:
                    task.cancel()
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
