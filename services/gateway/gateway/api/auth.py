from fastapi import APIRouter, Depends, Request, Response

from ..constants.http import PROXY_METHODS
from ..dependencies.jwt import get_current_claims
from ..utils.proxy import proxy_request

router = APIRouter(prefix="/auth/api/v1", tags=["auth"], include_in_schema=False)


@router.api_route("/{path:path}", methods=PROXY_METHODS, dependencies=[Depends(get_current_claims)])
@router.api_route("", methods=PROXY_METHODS, dependencies=[Depends(get_current_claims)])
@router.post("/check-account/{account_email}")
@router.post("/sign-up")
@router.post("/sign-up-complete")
@router.post("/employee-invite/{invite_token}")
@router.post("/login")
@router.post("/login-refresh")
async def proxy_auth_request(request: Request) -> Response:
    """Forward auth requests using the route's authentication policy."""
    return await proxy_request("auth", request)
