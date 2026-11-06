from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from shared.correlation.middleware import correlation_id_middleware
from shared.logging.config import setup_logging
from shared.resources.exceptions_handler import exception_handlers

from .api.operations import router as operations_router
from .api.v1.auth import router as auth_router
from .config import get_settings

setup_logging()

app = FastAPI(
    exception_handlers=exception_handlers,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_settings().allowed_hosts, www_redirect=False)

app.middleware("http")(correlation_id_middleware)

app.include_router(auth_router)
app.include_router(operations_router)
