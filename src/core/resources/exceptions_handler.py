import logging
from collections.abc import Callable, Coroutine
from http import HTTPStatus
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.core.resources.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainValidationError,
    NotFoundError,
)

logger = logging.getLogger(__name__)

ExceptionHandler = Callable[
    [Request, Exception],
    Coroutine[Any, Any, Response],
]


def _create_error_handler(status: HTTPStatus) -> ExceptionHandler:
    async def _error_handler(request: Request, exception: Exception) -> JSONResponse:
        logger.warning(f"Request failed: error={type(exception).__name__} detail={exception}")
        content = {}
        headers = {}

        if isinstance(exception, AuthenticationError):
            headers["WWW-Authenticate"] = "Bearer"
        content["detail"] = str(exception)

        return JSONResponse(
            status_code=status.value,
            content=content,
            headers=headers,
        )

    return _error_handler


async def _internal_error_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "-")

    logger.error(
        "Unexpected error while processing request",
        exc_info=exception,
        extra={"correlation_id": correlation_id},
    )

    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
        headers={"X-Correlation-ID": correlation_id},
    )


exception_handlers: dict[int | type[Exception], ExceptionHandler] = {
    AuthenticationError: _create_error_handler(HTTPStatus.UNAUTHORIZED),
    AuthorizationError: _create_error_handler(HTTPStatus.FORBIDDEN),
    ConflictError: _create_error_handler(HTTPStatus.CONFLICT),
    NotFoundError: _create_error_handler(HTTPStatus.NOT_FOUND),
    DomainValidationError: _create_error_handler(HTTPStatus.BAD_REQUEST),
    Exception: _internal_error_handler,
}
