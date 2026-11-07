from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient
from starlette.middleware.trustedhost import TrustedHostMiddleware

from shared.correlation.middleware import correlation_id_middleware
from shared.logging.config import setup_logging
from shared.resources.exceptions_handler import exception_handlers

from .api.metrics import router as metrics_router
from .api.operations import router as operations_router
from .config import get_settings
from .services.metrics_service import MetricsService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage the HTTP client used to collect upstream metrics."""
    settings = get_settings()
    async with AsyncClient(timeout=settings.upstream_http_timeout, follow_redirects=False) as client:
        app.state.metrics_service = MetricsService(
            client=client,
            service_urls=settings.service_urls,
            max_concurrency=settings.upstream_max_concurrency,
        )
        yield


setup_logging()

app = FastAPI(exception_handlers=exception_handlers, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_settings().allowed_hosts, www_redirect=False)
app.middleware("http")(correlation_id_middleware)
app.include_router(operations_router)
app.include_router(metrics_router)
