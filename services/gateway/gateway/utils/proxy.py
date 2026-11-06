from contextlib import aclosing
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException, Request, Response, status
from httpx import URL, AsyncClient, Headers, RequestError, TimeoutException
from httpx import Request as HttpRequest

from ..constants.http import HOP_BY_HOP_HEADERS
from ..constants.operations import OPERATION_PATHS


def filter_headers(headers: Headers) -> list[tuple[bytes, bytes]]:
    """Remove connection-specific headers while preserving repeated values."""
    connection_headers = {name.lower().encode("latin-1") for name in headers.get_list("connection", split_commas=True)}
    excluded = HOP_BY_HOP_HEADERS | connection_headers
    return [(name.lower(), value) for name, value in headers.raw if name.lower() not in excluded]


async def proxy_request(service: str, request: Request, operation: str | None = None) -> Response:
    """Forward business or explicitly allowed operational requests."""
    path = request.scope["path"].lstrip("/")
    base_url = request.app.state.upstream_urls.get(service)
    prefix = f"{service}/api/v1"
    allowed_path = path == prefix or path.startswith(f"{prefix}/")
    upstream_path = None
    if operation is not None:
        upstream_path = OPERATION_PATHS.get(service, {}).get(operation)
        allowed_path = upstream_path is not None
    has_dot_segment = any(part in {".", ".."} for part in path.split("/"))
    if base_url is None or not allowed_path or has_dot_segment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    raw_path = request.scope["raw_path"] if upstream_path is None else upstream_path.encode("ascii")
    if request.scope["query_string"]:
        raw_path += b"?" + request.scope["query_string"]
    url = URL(base_url).copy_with(raw_path=raw_path)
    headers = [
        (name, value)
        for name, value in filter_headers(Headers(request.headers.raw))
        if name not in {b"host", b"x-correlation-id"}
    ]
    headers.append((b"x-correlation-id", request.state.correlation_id.encode("ascii")))
    upstream_request = HttpRequest(request.method, url, headers=headers, content=await request.body())
    client: AsyncClient = request.app.state.upstream_http_client

    try:
        async with aclosing(await client.send(upstream_request, stream=True)) as upstream_response:
            content = b"".join([chunk async for chunk in upstream_response.aiter_raw()])
    except TimeoutException as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Upstream request timed out"
        ) from error
    except RequestError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Upstream service unavailable") from error
    finally:
        client.cookies.clear()
    response = Response(content=content, status_code=upstream_response.status_code)
    response.raw_headers = filter_headers(upstream_response.headers)
    location = upstream_response.headers.get("location")
    if location:
        redirect = urlsplit(location)
        if redirect.netloc == urlsplit(base_url).netloc:
            response.headers["location"] = urlunsplit(
                ("", "", redirect.path or "/", redirect.query, redirect.fragment)
            )
    return response
