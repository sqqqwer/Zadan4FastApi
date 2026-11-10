from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from redis.asyncio import Redis


@asynccontextmanager
async def redis_client(url: str) -> AsyncGenerator[Redis]:
    """Manage a Redis client shared by the application.

    Args:
        url: Redis connection URL.

    Yields:
        Redis: Connected client returning decoded strings.
    """
    client = Redis.from_url(url, decode_responses=True)
    try:
        await client.ping()
        yield client
    finally:
        await client.aclose()
