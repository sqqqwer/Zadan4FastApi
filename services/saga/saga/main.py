from fastapi import FastAPI

from shared.correlation.middleware import correlation_id_middleware
from shared.logging.config import setup_logging
from shared.resources.exceptions_handler import exception_handlers

from .api.operations import router as operations_router
from .api.v1.saga import router as saga_router

setup_logging()

app = FastAPI(exception_handlers=exception_handlers)
app.middleware("http")(correlation_id_middleware)
app.include_router(operations_router)
app.include_router(saga_router)
