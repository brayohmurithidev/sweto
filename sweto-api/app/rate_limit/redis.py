from redis.asyncio import Redis

from app.rate_limit.base import (
    RateLimiter,
    RateLimitResult,
)

FIXED_WINDOW_SCRIPT = """
local current = redis.call("INCR", KEYS[1])

if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end

local ttl = redis.call("TTL", KEYS[1])

return {current, ttl}
"""


class RedisRateLimiter(RateLimiter):
    """Fixed-window rate limiter backed by Redis."""

    def __init__(
        self,
        *,
        redis: Redis,
        key_prefix: str,
    ) -> None:
        self.redis = redis
        self.key_prefix = key_prefix

    async def consume(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        if limit <= 0:
            raise ValueError("Rate-limit value must be positive.")

        if window_seconds <= 0:
            raise ValueError("Rate-limit window must be positive.")

        redis_key = f"{self.key_prefix}:rate-limit:{key}"

        raw_result = await self.redis.eval(
            FIXED_WINDOW_SCRIPT,
            1,
            redis_key,
            window_seconds,
        )

        if not isinstance(raw_result, list) or len(raw_result) != 2:
            raise RuntimeError("Redis returned an unexpected rate-limit response.")

        count = int(raw_result[0])
        ttl = max(0, int(raw_result[1]))

        allowed = count <= limit
        remaining = max(0, limit - count)

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after_seconds=ttl if not allowed else 0,
        )
