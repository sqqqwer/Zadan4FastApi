from fastapi import APIRouter, Depends, Request, Response

from ..constants.http import PROXY_METHODS
from ..dependencies.jwt import get_current_claims
from ..utils.proxy import proxy_request

router = APIRouter(
    prefix="/org/api/v1", tags=["org"], dependencies=[Depends(get_current_claims)], include_in_schema=False
)


@router.api_route("", methods=PROXY_METHODS)
@router.api_route("/{path:path}", methods=PROXY_METHODS)
async def proxy_org_request(request: Request) -> Response:
    """Forward org requests after validating the access token."""
    return await proxy_request("org", request)
