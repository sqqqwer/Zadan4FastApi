from fastapi import APIRouter, Request, Response

from ..utils.proxy import proxy_request

router = APIRouter(tags=["operations"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Check HTTP liveness independently of upstream services."""
    return {"status": "ok"}


@router.get("/{service}/operations/{operation}", include_in_schema=False)
async def proxy_operation(service: str, operation: str, request: Request) -> Response:
    """Forward the explicitly allowed operational endpoints without a JWT."""
    return await proxy_request(service, request, operation=operation)
