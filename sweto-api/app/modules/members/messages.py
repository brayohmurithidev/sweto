"""SMS texts sent to gym members.

Every template stays within one 160-character GSM-7 segment for realistic
gym names (names are shortened to fit) and uses plain ASCII only: no emoji,
no curly quotes, which would switch the message to UCS-2 (70 characters).

The opt-out line is deliberately not "reply STOP": with an alphanumeric
sender ID the channel is one-way, so a reply would never arrive. Members
stop messages through the gym, which records the opt-out.
"""

from datetime import date
from decimal import Decimal

import phonenumbers

SMS_LIMIT = 160
_GYM_NAME_LIMIT = 24


def _gym(name: str) -> str:
    name = " ".join(name.split())
    return name if len(name) <= _GYM_NAME_LIMIT else name[: _GYM_NAME_LIMIT - 1] + "."


def _day(day: date) -> str:
    return f"{day.day} {day:%b %Y}"


def _money(amount: Decimal, currency: str) -> str:
    return f"{currency} {amount:,.0f}"


def _opt_out(gym_phone: str | None) -> str:
    if gym_phone:
        try:
            parsed = phonenumbers.parse(gym_phone)
            local = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.NATIONAL
            ).replace(" ", "")
        except phonenumbers.NumberParseException:
            local = gym_phone
        return f"To stop SMS, tell the gym or call {local}."
    return "To stop SMS, tell the gym."


def _period(paid_until: date, starts_on: date | None) -> str:
    """ "Paid until 13 Dec", or "Starts 17 Nov, paid until 16 Dec" when the
    period begins on a later day."""

    if starts_on is None:
        return f"Paid until {_day(paid_until)}"
    return f"Starts {_day(starts_on)}, paid until {_day(paid_until)}"


def welcome(
    *,
    gym_name: str,
    gym_phone: str | None,
    code: str,
    paid_until: date,
    starts_on: date | None = None,
) -> str:
    return (
        f"Welcome to {_gym(gym_name)}! Check-in code: {code}. Show it at the "
        f"door. {_period(paid_until, starts_on)}. {_opt_out(gym_phone)}"
    )


def payment_receipt(
    *,
    gym_name: str,
    gym_phone: str | None,
    amount: Decimal,
    currency: str,
    paid_until: date,
    starts_on: date | None = None,
) -> str:
    period = _period(paid_until, starts_on)
    return (
        f"{_gym(gym_name)}: received {_money(amount, currency)}. Membership "
        f"{period[0].lower()}{period[1:]}. {_opt_out(gym_phone)}"
    )


def check_in_code(*, gym_name: str, gym_phone: str | None, code: str) -> str:
    return (
        f"{_gym(gym_name)}: your new check-in code is {code}. The old code no "
        f"longer works. {_opt_out(gym_phone)}"
    )


def expiry_reminder(
    *, gym_name: str, gym_phone: str | None, ends_on: date, today: date
) -> str:
    when = "today" if ends_on == today else f"on {_day(ends_on)}"
    return (
        f"{_gym(gym_name)}: your membership ends {when}. Renew to keep "
        f"checking in. {_opt_out(gym_phone)}"
    )
