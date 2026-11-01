from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient

from shared.correlation.middleware import correlation_id_middleware
from shared.logging.config import setup_logging
from shared.resources.exceptions_handler import exception_handlers

from .api.v1.org import router
from .config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage the HTTP client used for the auth fallback."""
    settings = get_settings()
    async with AsyncClient(base_url=settings.auth_base_url, timeout=settings.auth_http_timeout) as client:
        app.state.auth_http_client = client
        yield


setup_logging()

app = FastAPI(
    exception_handlers=exception_handlers,
    lifespan=lifespan,
)
app.middleware("http")(correlation_id_middleware)
app.include_router(router)
