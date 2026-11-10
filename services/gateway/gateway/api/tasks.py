from fastapi import APIRouter, Depends, Request, Response

from ..constants.http import PROXY_METHODS
from ..dependencies.rate_limiter import check_rate_limit
from ..utils.proxy import proxy_request

router = APIRouter(
    prefix="/tasks/api/v1", tags=["tasks"], dependencies=[Depends(check_rate_limit)], include_in_schema=False
)


@router.api_route("", methods=PROXY_METHODS)
@router.api_route("/{path:path}", methods=PROXY_METHODS)
async def proxy_tasks_request(request: Request) -> Response:
    """Forward tasks requests after validating the access token."""
    return await proxy_request("tasks", request)
