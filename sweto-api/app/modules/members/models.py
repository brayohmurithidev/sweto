"""Members a gym runs through SWETO, their memberships and payments.

A gym member is a record the gym owns, not a SWETO user account, so owners
can add members who never install the app. In phase 2 a member who signs up
with the same phone number gets linked through ``user_id``.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.types import string_enum
from app.modules.gyms.enums import MembershipBillingPeriod
from app.modules.members.enums import (
    GymMembershipStatus,
    GymMemberStatus,
    PaymentMethod,
    PaymentStatus,
)


class GymMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gym_members"
    __table_args__ = (
        UniqueConstraint("gym_id", "phone_number", name="uq_gym_members_gym_phone"),
        Index("ix_gym_members_gym_status", "gym_id", "status"),
    )

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[GymMemberStatus] = mapped_column(
        string_enum(GymMemberStatus, name="gym_member_status"),
        nullable=False,
        default=GymMemberStatus.ACTIVE,
        server_default=GymMemberStatus.ACTIVE.value,
    )
    # Set when check-in codes are issued (build-order PR 4); only a hash is
    # stored, never the code itself.
    check_in_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    memberships: Mapped[list["GymMembership"]] = relationship(
        back_populates="member",
        cascade="all, delete-orphan",
        order_by="GymMembership.starts_on.desc()",
    )


class GymMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One paid period. A renewal is a new row, never an edit of the old one."""

    __tablename__ = "gym_memberships"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="period_order"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("status <> 'expired'", name="expired_is_derived"),
        Index("ix_gym_memberships_member_ends", "member_id", "ends_on"),
    )

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("gym_members.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("gym_membership_plans.id", ondelete="SET NULL"), nullable=True
    )
    # Snapshot of the plan when it was bought, so later price edits or a
    # deleted plan never rewrite history.
    plan_name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_period: Mapped[MembershipBillingPeriod] = mapped_column(
        String(30), nullable=False
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[GymMembershipStatus] = mapped_column(
        string_enum(GymMembershipStatus, name="gym_membership_status"),
        nullable=False,
    )

    member: Mapped[GymMember] = relationship(back_populates="memberships")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="membership",
        order_by="Payment.created_at",
    )


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Money received for a membership.

    One row per payment, whatever the method. Cash is recorded by staff and is
    complete at once. M-Pesa (build-order PR 6) will create a pending payment
    and keep each STK Push attempt and callback in a separate transactions
    table, completing the payment from there.
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "method <> 'cash' OR recorded_by_user_id IS NOT NULL",
            name="cash_has_recorder",
        ),
        Index("ix_payments_gym_paid_at", "gym_id", "paid_at"),
    )

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
    )
    membership_id: Mapped[UUID] = mapped_column(
        # NO ACTION (checked at the end of the statement) rather than
        # RESTRICT, so deleting a whole gym can still cascade through.
        ForeignKey("gym_memberships.id"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        string_enum(PaymentMethod, name="payment_method"), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        string_enum(PaymentStatus, name="payment_status"), nullable=False
    )
    payer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recorded_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    membership: Mapped[GymMembership] = relationship(back_populates="payments")
