"""Injectable clock, so tests can pin "now" at date boundaries."""

from collections.abc import Callable
from datetime import UTC, datetime

type Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def get_clock() -> Clock:
    """FastAPI dependency returning the current-time source."""

    return utc_now
