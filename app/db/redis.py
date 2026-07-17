from redis.asyncio import Redis

from app.core.config import Settings


def create_redis(settings: Settings) -> Redis:
    """Create an async Redis client."""
    return Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
