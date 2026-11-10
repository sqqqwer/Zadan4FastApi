from abc import ABC, abstractmethod
from typing import override

from redis.asyncio import Redis


class CacheAbstractService(ABC):
    """Abstract cache service."""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Get a cached value.

        Args:
            key: Cache key including the service and company scope.

        Returns:
            str: Cached serialized value.
            None: If the key is not found or has expired.
        """
        ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> None:
        """Save a value with an expiration time.

        Args:
            key: Cache key including the service and company scope.
            value: Serialized value, such as a JSON response.
            ttl: Positive expiration time in seconds.

        Raises:
            ValueError: If ttl is not positive.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Invalidate a cached value.

        Args:
            key: Cache key to delete after committing database changes.
        """
        ...


class CacheRedisService(CacheAbstractService):
    """Cache service using Redis."""

    def __init__(self, redis: Redis):
        """Initialize the cache service.

        Args:
            redis: Shared Redis client.
        """
        self.redis = redis

    @override
    async def get(self, key: str) -> str | None:
        value = await self.redis.get(f"cache:{key}")
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    @override
    async def set(self, key: str, value: str, ttl: int) -> None:
        if ttl <= 0:
            raise ValueError("Cache ttl must be positive.")
        await self.redis.set(f"cache:{key}", value, ex=ttl)

    @override
    async def delete(self, key: str) -> None:
        await self.redis.delete(f"cache:{key}")
