from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.gyms.enums import MembershipBillingPeriod
from app.modules.members.enums import (
    CheckInResult,
    GymMembershipStatus,
    GymMemberStatus,
    MemberMessageStatus,
    MemberStanding,
    PaymentMethod,
    PaymentStatus,
)


def _collapse_spaces(value: str) -> str:
    return " ".join(value.split())


class CreateGymMemberRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(min_length=3, max_length=32)
    sms_consent: bool = Field(
        default=False,
        description="Staff confirm the member agreed to SMS from the gym. "
        "Without it the member is added but gets no SMS.",
    )

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _collapse_spaces(value)


class UpdateGymMemberRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone_number: str | None = Field(default=None, min_length=3, max_length=32)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return None if value is None else _collapse_spaces(value)


class RecordCashPaymentRequest(BaseModel):
    plan_id: UUID
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Amount received. Defaults to the plan's price.",
    )
    starts_on: date | None = Field(
        default=None,
        description=(
            "First day of the membership, for a member who paid before being "
            "added. Only for a member with no current membership; not in the "
            "future and at most 90 days back. Without it, the membership "
            "starts the day after the current one ends, or today."
        ),
    )


class PaymentData(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    paid_at: datetime | None
    recorded_by_user_id: UUID | None


class GymMembershipData(BaseModel):
    id: UUID
    plan_id: UUID | None
    plan_name: str
    amount: Decimal
    currency: str
    billing_period: MembershipBillingPeriod
    starts_on: date
    ends_on: date
    status: GymMembershipStatus
    visit_limit: int | None
    payments: list[PaymentData]


class GymMemberData(BaseModel):
    id: UUID
    full_name: str
    phone_number: str
    status: GymMemberStatus
    standing: MemberStanding
    paid_until: date | None
    has_check_in_code: bool
    sms_enabled: bool
    sms_consent_recorded_at: datetime | None
    sms_opted_out_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GymMemberListData(BaseModel):
    members: list[GymMemberData]
    total: int
    limit: int
    offset: int


class GymMemberDetailData(BaseModel):
    member: GymMemberData
    memberships: list[GymMembershipData]


class SetMemberSmsRequest(BaseModel):
    enabled: bool = Field(
        description="true records that the member agreed (again) to SMS; "
        "false records that they asked to stop."
    )


class RecordCashPaymentData(BaseModel):
    member: GymMemberData
    membership: GymMembershipData
    sms: MemberMessageStatus | None = Field(
        default=None,
        description="Welcome or receipt SMS outcome; null when none was sent "
        "(no consent, opted out).",
    )


class CheckInCodeData(BaseModel):
    """Shown once: only a hash is kept, so a lost code is replaced, not shown."""

    member_id: UUID
    code: str = Field(description="Display form, e.g. 7KQ2-M9XD.")
    qr_payload: str = Field(description="What the member's QR code encodes.")
    sms: MemberMessageStatus | None = Field(
        default=None, description="Outcome of texting the code to the member."
    )


class CheckInRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=64,
        description="Typed code (any case, dashes and spaces ignored) or the "
        "scanned QR payload.",
    )


class CheckInMemberData(BaseModel):
    id: UUID
    full_name: str
    standing: MemberStanding
    paid_until: date | None


class CheckInMembershipData(BaseModel):
    plan_name: str
    starts_on: date
    ends_on: date
    visit_limit: int | None
    visits_used: int


class CheckInData(BaseModel):
    id: UUID
    result: CheckInResult
    allowed: bool
    already_checked_in_today: bool
    message: str
    checked_in_at: datetime
    member: CheckInMemberData | None
    membership: CheckInMembershipData | None


class CheckInLogEntry(BaseModel):
    id: UUID
    result: CheckInResult
    already_checked_in_today: bool
    checked_in_at: datetime
    member_id: UUID | None
    member_name: str | None


class CheckInDayData(BaseModel):
    date: date
    visits: int = Field(description="Members let in, each counted once a day.")
    refused: int
    check_ins: list[CheckInLogEntry]


class RequestMpesaPaymentRequest(BaseModel):
    plan_id: UUID
    amount: int | None = Field(
        default=None,
        gt=0,
        le=250_000,
        description="Whole KES. Defaults to the plan's price.",
    )
    phone_number: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
        description="Phone to prompt; defaults to the member's own number.",
    )


class MpesaPaymentData(BaseModel):
    payment_id: UUID
    member_id: UUID
    status: PaymentStatus
    amount: Decimal
    currency: str
    plan_name: str
    message: str = Field(description="Plain words for staff about where it stands.")
    receipt: str | None = None
    paid_until: date | None = None
    sms: MemberMessageStatus | None = None


class DailyRevenue(BaseModel):
    date: date
    amount: Decimal


class RevenueSummary(BaseModel):
    currency: str
    this_month: Decimal
    last_month: Decimal
    change_percent: float | None = Field(
        description="This month so far against all of last month; null when "
        "last month had no revenue."
    )
    daily: list[DailyRevenue] = Field(
        description="Each day of this month up to today, zeros included."
    )


class ActivityItem(BaseModel):
    kind: str = Field(description="check_in, payment or member_added")
    at: datetime
    member_id: UUID | None
    member_name: str | None
    detail: str
    ok: bool


class DashboardData(BaseModel):
    gym_name: str
    owner_first_name: str | None
    today: date
    active_members: int
    expiring_members: int
    check_ins_today: int
    revenue: RevenueSummary
    recent_activity: list[ActivityItem]
