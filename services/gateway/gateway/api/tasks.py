from fastapi import APIRouter, Depends, Request, Response

from ..constants.http import PROXY_METHODS
from ..dependencies.jwt import get_current_claims
from ..utils.proxy import proxy_request

router = APIRouter(
    prefix="/tasks/api/v1", tags=["tasks"], dependencies=[Depends(get_current_claims)], include_in_schema=False
)


@router.api_route("", methods=PROXY_METHODS)
@router.api_route("/{path:path}", methods=PROXY_METHODS)
async def proxy_tasks_request(request: Request) -> Response:
    """Forward tasks requests after validating the access token."""
    return await proxy_request("tasks", request)
