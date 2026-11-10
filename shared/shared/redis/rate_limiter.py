from abc import ABC, abstractmethod
from typing import override
from uuid import uuid4

from redis.asyncio import Redis

RATE_LIMIT_SCRIPT = """
local now = redis.call("TIME")
local current_ms = tonumber(now[1]) * 1000 + math.floor(tonumber(now[2]) / 1000)
local window_ms = tonumber(ARGV[2]) * 1000

redis.call("ZREMRANGEBYSCORE", KEYS[1], "-inf", current_ms - window_ms)
local count = redis.call("ZCARD", KEYS[1])
if count >= tonumber(ARGV[1]) then
    return 1
end

redis.call("ZADD", KEYS[1], current_ms, ARGV[3])
redis.call("EXPIRE", KEYS[1], ARGV[2])
return 0
"""


class RateLimiterAbstractService(ABC):
    """Abstract rate limiter service."""

    @abstractmethod
    async def is_limited(
        self,
        identifier: str,
        endpoint: str,
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        """Check the limit and record an allowed request.

        Args:
            identifier: Trusted user ID or another identifier selected by the caller.
            endpoint: Service and operation scope sharing the same request budget.
            max_requests: Positive maximum number of requests in the window.
            window_seconds: Positive sliding window duration in seconds.

        Returns:
            bool: True if the request exceeds the limit.

        Raises:
            ValueError: If max_requests or window_seconds is not positive.
        """
        ...


class RateLimiterRedisService(RateLimiterAbstractService):
    """Rate limiter using an atomic Redis sliding window."""

    def __init__(self, redis: Redis):
        """Initialize the rate limiter service.

        Args:
            redis: Shared Redis client used to execute the Lua script.
        """
        self.redis = redis
        self._script = redis.register_script(RATE_LIMIT_SCRIPT)

    @override
    async def is_limited(
        self,
        identifier: str,
        endpoint: str,
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        if max_requests <= 0 or window_seconds <= 0:
            raise ValueError("Rate limit and window must be positive.")

        key = f"rate_limiter:{len(endpoint)}:{endpoint}:{identifier}"
        result = await self._script(
            keys=[key],
            args=[max_requests, window_seconds, str(uuid4())],
        )
        return result == 1
