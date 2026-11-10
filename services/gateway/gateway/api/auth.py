from fastapi import APIRouter, Depends, Request, Response

from ..constants.http import PROXY_METHODS
from ..dependencies.rate_limiter import check_public_rate_limit, check_rate_limit
from ..utils.proxy import proxy_request

router = APIRouter(tags=["auth"], include_in_schema=False)
public_router = APIRouter(prefix="/auth/api/v1", dependencies=[Depends(check_public_rate_limit)])
protected_router = APIRouter(prefix="/auth/api/v1", dependencies=[Depends(check_rate_limit)])


@protected_router.api_route("/{path:path}", methods=PROXY_METHODS)
@protected_router.api_route("", methods=PROXY_METHODS)
@public_router.post("/check-account/{account_email}")
@public_router.post("/sign-up")
@public_router.post("/sign-up-complete")
@public_router.post("/employee-invite/{invite_token}")
@public_router.post("/login")
@public_router.post("/login-refresh")
async def proxy_auth_request(request: Request) -> Response:
    """Forward auth requests using the route's authentication policy."""
    return await proxy_request("auth", request)


router.include_router(public_router)
router.include_router(protected_router)
