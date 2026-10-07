from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.rate_limit.base import (
    RateLimiter,
    RateLimitResult,
)


@dataclass(slots=True)
class MemoryBucket:
    """One in-memory fixed-window bucket."""

    count: int
    expires_at: datetime


class MemoryRateLimiter(RateLimiter):
    """In-memory rate limiter for tests and local unit isolation."""

    def __init__(self) -> None:
        self.buckets: dict[str, MemoryBucket] = {}

    async def consume(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        now = datetime.now(UTC)

        bucket = self.buckets.get(key)

        if bucket is None or now >= bucket.expires_at:
            bucket = MemoryBucket(
                count=0,
                expires_at=now + timedelta(seconds=window_seconds),
            )
            self.buckets[key] = bucket

        bucket.count += 1

        allowed = bucket.count <= limit
        remaining = max(0, limit - bucket.count)
        retry_after_seconds = max(
            0,
            int((bucket.expires_at - now).total_seconds()),
        )

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after_seconds=(retry_after_seconds if not allowed else 0),
        )
