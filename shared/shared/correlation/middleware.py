from collections.abc import Callable
from uuid import UUID, uuid4

from fastapi import Request

from .request_context import correlation_id_var


async def correlation_id_middleware(request: Request, call_next: Callable):
    """Set the request correlation ID and add it to the response headers.

    Args:
        request: FastAPI request object.
        call_next: Callable that processes the next step of the request.

    Returns:
        Response: Response with the X-Correlation-ID header.
    """
    incoming_id = request.headers.get("X-Correlation-ID")

    try:
        correlation_id = str(UUID(incoming_id)) if incoming_id else str(uuid4())
    except ValueError:
        correlation_id = str(uuid4())

    token = correlation_id_var.set(correlation_id)
    request.state.correlation_id = correlation_id

    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    finally:
        correlation_id_var.reset(token)
