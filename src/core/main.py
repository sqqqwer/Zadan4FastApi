from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.events.bus import InMemoryEventBus
from src.core.logging.config import setup_logging
from src.core.resources.exceptions_handler import exception_handlers
from src.modules.auth.api.v1.auth import router as auth_router
from src.modules.auth.events import subscribe_handlers as auth_subscribe_handlers
from src.modules.org.api.v1.org import router as org_router
from src.modules.org.events import subscribe_handlers as org_subscribe_handlers
from src.modules.tasks.api.v1.tasks import router as tasks_router
from src.modules.tasks.events import subscribe_handlers as tasks_subscribe_handlers

from .middleware import correlation_id_middleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Set up the event bus and handlers for the application.

    Args:
        app: FastAPI application.

    Yields:
        None: Control while the application is running.
    """
    bus = InMemoryEventBus()

    await auth_subscribe_handlers(bus)
    await org_subscribe_handlers(bus)
    await tasks_subscribe_handlers(bus)

    app.state.event_bus = bus

    yield


setup_logging()

app = FastAPI(
    exception_handlers=exception_handlers,
    lifespan=lifespan,
)

app.middleware("http")(correlation_id_middleware)

app.include_router(auth_router)
app.include_router(org_router)
app.include_router(tasks_router)
