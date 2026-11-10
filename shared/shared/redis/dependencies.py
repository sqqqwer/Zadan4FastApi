from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from .cache import CacheAbstractService, CacheRedisService
from .rate_limiter import RateLimiterAbstractService, RateLimiterRedisService


def get_redis(request: Request) -> Redis:
    """Get the Redis client managed by the application lifespan.

    Args:
        request: Current request containing the application state.

    Returns:
        Redis: Shared client stored in app.state.redis.
    """
    return request.app.state.redis


RedisDependency = Annotated[Redis, Depends(get_redis)]


def get_cache_service(redis: RedisDependency) -> CacheAbstractService:
    """Get the cache service.

    Args:
        redis: Shared Redis client.

    Returns:
        CacheAbstractService: Cache service using Redis.
    """
    return CacheRedisService(redis=redis)


def get_rate_limiter_service(redis: RedisDependency) -> RateLimiterAbstractService:
    """Get the rate limiter service.

    Args:
        redis: Shared Redis client.

    Returns:
        RateLimiterAbstractService: Rate limiter service using Redis.
    """
    return RateLimiterRedisService(redis=redis)


CacheServiceDependency = Annotated[CacheAbstractService, Depends(get_cache_service)]
RateLimiterServiceDependency = Annotated[RateLimiterAbstractService, Depends(get_rate_limiter_service)]
