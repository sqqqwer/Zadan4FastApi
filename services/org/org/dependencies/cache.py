from typing import Annotated

from fastapi import Depends

from shared.redis.dependencies import CacheServiceDependency, RedisDependency

from ..config import get_settings
from ..services.struct_cache import StructCacheService
from .jwt import AccessTokenClaimsDependency


def get_struct_cache_service(
    cache: CacheServiceDependency,
    redis: RedisDependency,
    claims: AccessTokenClaimsDependency,
) -> StructCacheService:
    """Get the struct cache for the current company.

    Args:
        cache: Shared cache service.
        redis: Redis client managed by the application lifespan.
        claims: Current user access token claims.

    Returns:
        StructCacheService: Company scoped cache with the configured lifetime.
    """
    return StructCacheService(
        cache=cache, redis=redis, company_id=claims.company_id, ttl=get_settings().struct_cache_ttl
    )


StructCacheServiceDependency = Annotated[StructCacheService, Depends(get_struct_cache_service)]
