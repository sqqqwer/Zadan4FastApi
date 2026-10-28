from typing import Annotated

from fastapi import Depends, Request
from httpx import AsyncClient


def get_auth_http_client(request: Request) -> AsyncClient:
    """Get the HTTP client managed by the application lifespan.

    Args:
        request: Current request containing the application state.

    Returns:
        AsyncClient: Shared client configured with the auth URL and timeout.
    """
    return request.app.state.auth_http_client


AuthHttpClientDependency = Annotated[AsyncClient, Depends(get_auth_http_client)]
