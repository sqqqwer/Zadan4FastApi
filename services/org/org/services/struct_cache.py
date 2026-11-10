import logging
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from shared.redis.cache import CacheAbstractService

logger = logging.getLogger(__name__)


class StructCacheService:
    """Cache company struct responses using an expiring generation."""

    def __init__(self, cache: CacheAbstractService, redis: Redis, company_id: UUID, ttl: int):
        """Initialize the struct cache.

        Args:
            cache: Service for reading and saving serialized responses.
            redis: Shared Redis client used to rotate the generation.
            company_id: Company whose structs are cached.
            ttl: Positive lifetime of cache values and their generation in seconds.
        """
        self.cache = cache
        self.redis = redis
        self.company_id = company_id
        self.ttl = ttl
        self._prefix = f"org:struct:v1:{company_id}"
        self._generation_key = f"cache:{self._prefix}:generation"

    async def get_key(self, operation: str) -> str | None:
        """Get a generation key before reading the database.

        Args:
            operation: Read operation including its ID or pagination parameters.

        Returns:
            str: Company and generation scoped response key.
            None: If Redis is unavailable or the generation has just expired.
        """
        try:
            await self.redis.set(self._generation_key, str(uuid4()), nx=True, ex=self.ttl)
            generation = await self.redis.get(self._generation_key)
            if generation is None:
                return None
            if isinstance(generation, bytes):
                generation = generation.decode("utf-8")
            return f"{self._prefix}:{generation}:{operation}"
        except RedisError:
            logger.warning(f"Struct cache generation unavailable: company_id={self.company_id}.")
            return None

    async def get[Response](self, key: str | None, adapter: TypeAdapter[Response]) -> Response | None:
        """Get and validate a cached response.

        Args:
            key: Generation scoped cache key, or None to bypass Redis.
            adapter: Schema adapter used to validate the cached JSON.

        Returns:
            Response: Validated cached response.
            None: If the value is missing, invalid or Redis is unavailable.
        """
        if key is None:
            return None
        try:
            value = await self.cache.get(key)
            return adapter.validate_json(value) if value is not None else None
        except (RedisError, ValidationError):
            logger.warning(f"Struct cache read failed: company_id={self.company_id}.")
            return None

    async def set[Response](self, key: str | None, response: Response, adapter: TypeAdapter[Response]) -> None:
        """Save the response in the generation selected before the database read.

        Args:
            key: Generation scoped cache key, or None to bypass Redis.
            response: Response loaded from the database.
            adapter: Schema adapter used to serialize the response as JSON.
        """
        if key is None:
            return
        try:
            await self.cache.set(key, adapter.dump_json(response).decode("utf-8"), ttl=self.ttl)
        except RedisError:
            logger.warning(f"Struct cache write failed: company_id={self.company_id}.")

    async def invalidate(self) -> None:
        """Rotate the company generation after committing a struct change."""
        try:
            await self.redis.set(self._generation_key, str(uuid4()), ex=self.ttl)
        except RedisError:
            logger.warning(f"Struct cache invalidation failed: company_id={self.company_id} ttl={self.ttl}.")
