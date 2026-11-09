from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from shared.correlation.middleware import correlation_id_middleware
from shared.logging.config import setup_logging
from shared.resources.exceptions_handler import exception_handlers
from shared.tracing.instrumentation import instrument_app, instrument_databases

from .api.operations import router as operations_router
from .api.v1.auth import router as auth_router
from .config import get_settings
from .database import async_engine
from .dependencies.tracing import get_tracing_reporter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage database tracing and finish pending exports on shutdown."""
    tracing = get_tracing_reporter()
    async with tracing.running() if tracing is not None else nullcontext():
        try:
            if tracing is not None:
                instrument_databases([async_engine], tracing)
            yield
        finally:
            await async_engine.dispose()


setup_logging()

app = FastAPI(
    exception_handlers=exception_handlers,
    lifespan=lifespan,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_settings().allowed_hosts, www_redirect=False)

app.middleware("http")(correlation_id_middleware)

app.include_router(auth_router)
app.include_router(operations_router)

tracing = get_tracing_reporter()
if tracing is not None:
    instrument_app(app, tracing, excluded_urls=get_settings().tracing_excluded_urls)
