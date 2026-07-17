import pytest

from app.rate_limit.memory import MemoryRateLimiter


@pytest.mark.asyncio
async def test_memory_rate_limiter_allows_within_limit() -> None:
    limiter = MemoryRateLimiter()

    first = await limiter.consume(
        key="otp:test",
        limit=2,
        window_seconds=60,
    )

    second = await limiter.consume(
        key="otp:test",
        limit=2,
        window_seconds=60,
    )

    assert first.allowed is True
    assert first.remaining == 1

    assert second.allowed is True
    assert second.remaining == 0


@pytest.mark.asyncio
async def test_memory_rate_limiter_blocks_over_limit() -> None:
    limiter = MemoryRateLimiter()

    await limiter.consume(
        key="otp:test",
        limit=1,
        window_seconds=60,
    )

    blocked = await limiter.consume(
        key="otp:test",
        limit=1,
        window_seconds=60,
    )

    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after_seconds > 0


@pytest.mark.asyncio
async def test_memory_rate_limiter_uses_independent_keys() -> None:
    limiter = MemoryRateLimiter()

    await limiter.consume(
        key="phone:one",
        limit=1,
        window_seconds=60,
    )

    other = await limiter.consume(
        key="phone:two",
        limit=1,
        window_seconds=60,
    )

    assert other.allowed is True
