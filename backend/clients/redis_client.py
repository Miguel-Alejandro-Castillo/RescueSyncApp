import os

from redis.asyncio import Redis


REDIS_URL = os.getenv("REDIS_URL")
REDIS_DECODE_RESPONSES = os.getenv("REDIS_DECODE_RESPONSES")


async def init_redis() -> Redis:
    redis = Redis.from_url(
        REDIS_URL,
        decode_responses=REDIS_DECODE_RESPONSES,
    )
    await redis.ping()
    return redis


async def close_redis(redis: Redis | None) -> None:
    if redis is None:
        return

    await redis.aclose()