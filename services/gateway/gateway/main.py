from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI
from httpx import AsyncClient
from starlette.middleware.trustedhost import TrustedHostMiddleware

from shared.correlation.middleware import correlation_id_middleware
from shared.logging.config import setup_logging
from shared.resources.exceptions_handler import exception_handlers
from shared.tracing.instrumentation import instrument_app, instrument_http_client

from .api.auth import router as auth_router
from .api.docs import router as docs_router
from .api.operations import router as operations_router
from .api.org import router as org_router
from .api.tasks import router as tasks_router
from .config import get_settings
from .dependencies.tracing import get_tracing_reporter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage tracing and the HTTP client used for upstream requests."""
    settings = get_settings()
    tracing = get_tracing_reporter()
    async with (
        tracing.running() if tracing is not None else nullcontext(),
        AsyncClient(timeout=settings.upstream_http_timeout, follow_redirects=False) as client,
    ):
        if tracing is not None:
            instrument_http_client(client, tracing)
        app.state.upstream_http_client = client
        app.state.upstream_urls = {
            "auth": settings.auth_base_url,
            "org": settings.org_base_url,
            "tasks": settings.tasks_base_url,
            "saga": settings.saga_base_url,
        }
        yield


setup_logging()

app = FastAPI(exception_handlers=exception_handlers, lifespan=lifespan, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_settings().allowed_hosts, www_redirect=False)
app.middleware("http")(correlation_id_middleware)
app.include_router(docs_router)
app.include_router(operations_router)
app.include_router(auth_router)
app.include_router(org_router)
app.include_router(tasks_router)

tracing = get_tracing_reporter()
if tracing is not None:
    instrument_app(app, tracing, excluded_urls=get_settings().tracing_excluded_urls)
