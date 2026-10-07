from functools import lru_cache

from app.core.config import get_settings
from app.core.redis import redis_client
from app.rate_limit.base import RateLimiter
from app.rate_limit.redis import RedisRateLimiter


@lru_cache
def get_rate_limiter() -> RateLimiter:
    """Return the configured production rate limiter."""

    settings = get_settings()

    return RedisRateLimiter(
        redis=redis_client,
        key_prefix=settings.redis_key_prefix,
    )
