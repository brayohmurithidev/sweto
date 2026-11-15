"""Membership period dates."""

import calendar
from datetime import date, timedelta

from app.modules.gyms.enums import MembershipBillingPeriod

EXPIRING_WITHIN_DAYS = 7
# A membership paid now can start up to this many days later.
FUTURE_START_LIMIT_DAYS = 30
"""A membership ending today or in the next 6 days counts as expiring."""

_MONTHS = {
    MembershipBillingPeriod.MONTHLY: 1,
    MembershipBillingPeriod.QUARTERLY: 3,
    MembershipBillingPeriod.SEMI_ANNUAL: 6,
    MembershipBillingPeriod.ANNUAL: 12,
}


def add_months(day: date, months: int) -> date:
    """Same day ``months`` later, clamped to the end of a shorter month."""

    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def period_end(starts_on: date, billing_period: MembershipBillingPeriod) -> date:
    """Last day (inclusive) of a period starting on ``starts_on``.

    A weekly plan bought on Monday runs to Sunday; a monthly plan bought on
    14 Nov runs to 13 Dec.
    """

    if billing_period == MembershipBillingPeriod.WEEKLY:
        return starts_on + timedelta(days=6)
    return add_months(starts_on, _MONTHS[billing_period]) - timedelta(days=1)
