from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.gyms.enums import MembershipBillingPeriod
from app.modules.members.enums import (
    GymMembershipStatus,
    GymMemberStatus,
    MemberStanding,
    PaymentMethod,
    PaymentStatus,
)


def _collapse_spaces(value: str) -> str:
    return " ".join(value.split())


class CreateGymMemberRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(min_length=3, max_length=32)

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
    payments: list[PaymentData]


class GymMemberData(BaseModel):
    id: UUID
    full_name: str
    phone_number: str
    status: GymMemberStatus
    standing: MemberStanding
    paid_until: date | None
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


class RecordCashPaymentData(BaseModel):
    member: GymMemberData
    membership: GymMembershipData
