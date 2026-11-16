from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

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
            "added, or a later day for one who pays now and starts later. "
            "Only for a member with no current membership; at most 90 days "
            "back and 30 days ahead. Without it, the membership starts the "
            "day after the current one ends, or today."
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
    starts_on: date | None = Field(
        default=None,
        description="First day of the period covering today, or of the next "
        "paid one when it hasn't started yet (standing upcoming).",
    )
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
    by_user_id: UUID | None = Field(
        default=None, description="The staff member who did it, when known."
    )
    by_name: str | None = Field(
        default=None, description="Their name, when they have one on file."
    )


class ActivityPageData(BaseModel):
    items: list[ActivityItem]
    has_more: bool
    limit: int
    offset: int


class DashboardData(BaseModel):
    gym_name: str
    owner_first_name: str | None
    today: date
    active_members: int
    expiring_members: int
    check_ins_today: int
    revenue: RevenueSummary | None = Field(
        default=None,
        description="Null when the caller's role may not see the gym's finances.",
    )
    recent_activity: list[ActivityItem]


class MethodTotal(BaseModel):
    method: PaymentMethod
    amount: Decimal
    count: int


class PlanTotal(BaseModel):
    plan_name: str
    amount: Decimal
    count: int


class MonthTotal(BaseModel):
    month: date = Field(description="First day of the month.")
    amount: Decimal


class FinanceSummaryData(BaseModel):
    currency: str
    month: date = Field(description="First day of the month shown.")
    through: date = Field(
        description="Last day counted: today for the current month, else the "
        "month's last day."
    )
    is_current_month: bool
    total: Decimal
    payments_count: int
    previous_month_total: Decimal = Field(
        description="The month before, over the same days of the month as "
        "``through`` so a month in progress is compared fairly."
    )
    change_percent: float | None = Field(
        description="Null when the month before had no revenue in that span."
    )
    by_method: list[MethodTotal] = Field(description="Cash and M-Pesa, always both.")
    by_plan: list[PlanTotal] = Field(description="Largest first.")
    trend: list[MonthTotal] = Field(
        description="Six months ending with this one, oldest first."
    )
    failed_mpesa_count: int = Field(
        description="M-Pesa prompts this month that failed or were cancelled."
    )
    pending_mpesa_count: int = Field(
        description="M-Pesa prompts this month still waiting for an answer."
    )


class FinanceTransactionData(BaseModel):
    payment_id: UUID
    member_id: UUID
    member_name: str
    plan_name: str
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    at: datetime = Field(description="When it was paid, or asked for if not paid.")
    receipt: str | None = Field(description="M-Pesa receipt number, when paid.")
    recorded_by_name: str | None = Field(description="Who recorded a cash payment.")


class FinanceTransactionListData(BaseModel):
    transactions: list[FinanceTransactionData]
    total: int
    limit: int
    offset: int


class SaveMpesaAccountRequest(BaseModel):
    account_type: Literal["paybill", "till"]
    shortcode: str = Field(
        pattern=r"^\d{5,7}$",
        description="Pay Bill number, or the store/head-office number that "
        "owns the till.",
    )
    till_number: str | None = Field(
        default=None,
        pattern=r"^\d{5,7}$",
        description="Required for a till: where the money goes.",
    )
    passkey: str | None = Field(
        default=None,
        min_length=20,
        max_length=128,
        description="Lipa na M-Pesa Online passkey from Safaricom. Required "
        "the first time; leave out to keep the saved one.",
    )
    consumer_key: str | None = Field(
        default=None,
        min_length=10,
        max_length=128,
        description="Consumer key of the gym's own Daraja app (gone live on "
        "this shortcode). Send with consumer_secret; leave both out to keep "
        "the saved ones.",
    )
    consumer_secret: str | None = Field(
        default=None,
        min_length=10,
        max_length=128,
        description="Consumer secret of the gym's own Daraja app.",
    )

    @model_validator(mode="after")
    def till_needs_number(self) -> "SaveMpesaAccountRequest":
        if self.account_type == "till" and not self.till_number:
            raise ValueError("A till needs its till number.")
        return self


class MpesaAccountData(BaseModel):
    configured: bool
    account_type: str | None = None
    shortcode: str | None = None
    till_number: str | None = None
    passkey_saved: bool = False
    app_keys_saved: bool = Field(
        default=False,
        description="Whether the gym's own Daraja consumer key and secret are "
        "saved. They are never sent back.",
    )
    updated_at: datetime | None = None
    mode: str = Field(description="disabled, simulated, sandbox or production")
