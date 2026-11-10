from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from shared.redis.dependencies import RateLimiterServiceDependency
from shared.redis.rate_limiter import RateLimiterAbstractService

from ..config import get_settings
from .jwt import AccessTokenClaimsDependency


async def check_rate_limit(
    claims: AccessTokenClaimsDependency,
    rate_limiter: RateLimiterServiceDependency,
) -> None:
    """Limit authenticated API requests by the verified user ID.

    Args:
        claims: Current user access token claims.
        rate_limiter: Shared Redis rate limiter service.

    Raises:
        HTTPException: If the limit is exceeded or Redis is unavailable.
    """
    await _check_rate_limit(
        identifier=str(claims.sub),
        endpoint="gateway:api",
        rate_limiter=rate_limiter,
    )


async def check_public_rate_limit(request: Request, rate_limiter: RateLimiterServiceDependency) -> None:
    """Limit public auth requests by the client IP address.

    Args:
        request: Current request containing the client address.
        rate_limiter: Shared Redis rate limiter service.

    Raises:
        HTTPException: If the address is missing, the limit is exceeded or Redis is unavailable.
    """
    if request.client is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client address unavailable.")

    await _check_rate_limit(
        identifier=request.client.host,
        endpoint="gateway:auth:public",
        rate_limiter=rate_limiter,
    )


async def _check_rate_limit(identifier: str, endpoint: str, rate_limiter: RateLimiterAbstractService) -> None:
    """Check the configured Redis request budget for the selected scope."""
    settings = get_settings()

    try:
        limited = await rate_limiter.is_limited(
            identifier=identifier,
            endpoint=endpoint,
            max_requests=settings.rate_limit_max_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
    except RedisError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter temporarily unavailable.",
        ) from error

    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please retry later.",
        )
