from enum import StrEnum


class GymMemberStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class GymMembershipStatus(StrEnum):
    """Lifecycle of one membership period.

    Only ``pending_payment``, ``active`` and ``cancelled`` are stored.
    ``expired`` is never written: an active membership whose ``ends_on`` is
    before the gym's local today is reported as expired, so validity always
    follows the dates.
    """

    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class MemberStanding(StrEnum):
    """Where a member stands today, from their latest paid membership."""

    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    NO_MEMBERSHIP = "no_membership"


class CheckInResult(StrEnum):
    ALLOWED = "allowed"
    EXPIRED = "expired"
    NOT_STARTED = "not_started"
    NO_MEMBERSHIP = "no_membership"
    ARCHIVED = "archived"
    VISIT_LIMIT_REACHED = "visit_limit_reached"
    UNKNOWN_CODE = "unknown_code"


class PaymentMethod(StrEnum):
    CASH = "cash"
    MPESA = "mpesa"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
