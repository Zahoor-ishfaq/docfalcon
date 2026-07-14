from functools import lru_cache
from upstash_redis import Redis
from backend.core.config import settings
import logging

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def _client() -> Redis | None:
    if not settings.REDIS_URL or not settings.REDIS_TOKEN:
        logger.warning("Redis not configured — caching disabled")
        return None
    return Redis(url=settings.REDIS_URL, token=settings.REDIS_TOKEN)

async def cache_get(key: str) -> str | None:
    try:
        client = _client()
        return client.get(key) if client else None
    except Exception as e:
        logger.warning("cache_get failed: %s", e)
        return None

async def cache_set(key: str, value: str, ttl: int) -> None:
    try:
        client = _client()
        if client:
            client.set(key, value, ex=ttl)
    except Exception as e:
        logger.warning("cache_set failed: %s", e)

async def cache_delete(key: str) -> None:
    try:
        client = _client()
        if client:
            client.delete(key)
    except Exception as e:
        logger.warning("cache_delete failed: %s", e)