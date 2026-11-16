"""Members a gym runs through SWETO, their memberships and payments.

A gym member is a record the gym owns, not a SWETO user account, so owners
can add members who never install the app. In phase 2 a member who signs up
with the same phone number gets linked through ``user_id``.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.types import string_enum
from app.modules.gyms.enums import MembershipBillingPeriod
from app.modules.members.enums import (
    CheckInResult,
    GymMembershipStatus,
    GymMemberStatus,
    MemberMessageKind,
    MemberMessageStatus,
    PaymentMethod,
    PaymentStatus,
    PaymentTransactionStatus,
)


class GymMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gym_members"
    __table_args__ = (
        UniqueConstraint("gym_id", "phone_number", name="uq_gym_members_gym_phone"),
        UniqueConstraint(
            "gym_id", "check_in_code_hash", name="uq_gym_members_gym_check_in_code"
        ),
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
    # Keyed hash (HMAC) of the member's check-in code; the code itself is
    # shown once when issued and never stored. Issuing a new one replaces it.
    check_in_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # SMS needs the member's agreement, confirmed by staff when they record
    # it. An opt-out wins until consent is recorded again.
    sms_consent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    sms_consent_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sms_consent_recorded_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sms_opted_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # The staff member who added them (for the gym's activity log).
    added_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    @property
    def can_receive_sms(self) -> bool:
        return self.sms_consent and self.sms_opted_out_at is None

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
    # Plan's visit limit when it was bought (null = unlimited).
    visit_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

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


class GymCheckIn(UUIDPrimaryKeyMixin, Base):
    """One attempt at the door, allowed or not.

    Refusals are kept too, so owners can see who tried to enter on an expired
    plan. An unknown code has no member.
    """

    __tablename__ = "gym_check_ins"
    __table_args__ = (
        Index("ix_gym_check_ins_gym_checked_in_at", "gym_id", "checked_in_at"),
        Index("ix_gym_check_ins_membership", "membership_id"),
    )

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
    )
    member_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("gym_members.id", ondelete="CASCADE"), nullable=True, index=True
    )
    membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("gym_memberships.id", ondelete="SET NULL"), nullable=True
    )
    result: Mapped[CheckInResult] = mapped_column(
        string_enum(CheckInResult, name="check_in_result"), nullable=False
    )
    # A second allowed check-in on the same local day: let in, not a new visit.
    repeat_visit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    checked_in_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class MemberMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One SMS to a member, so each notice goes out once.

    The text is not stored: a welcome or code message contains a check-in
    code, and only the code's hash may be kept.
    """

    __tablename__ = "member_messages"
    __table_args__ = (
        # One welcome per member; one receipt and one of each reminder per
        # membership period. Check-in code messages repeat by design.
        Index(
            "uq_member_messages_welcome",
            "member_id",
            unique=True,
            postgresql_where=text("kind = 'welcome'"),
        ),
        Index(
            "uq_member_messages_membership_kind",
            "membership_id",
            "kind",
            unique=True,
            postgresql_where=text(
                "kind IN ('payment_receipt', 'expiry_reminder_3_days', "
                "'expiry_reminder_today')"
            ),
        ),
        Index("ix_member_messages_gym_created", "gym_id", "created_at"),
    )

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
    )
    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("gym_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    membership_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("gym_memberships.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[MemberMessageKind] = mapped_column(
        string_enum(MemberMessageKind, name="member_message_kind"), nullable=False
    )
    status: Mapped[MemberMessageStatus] = mapped_column(
        string_enum(MemberMessageStatus, name="member_message_status"),
        nullable=False,
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PaymentTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One attempt to collect a payment through a provider (an STK Push).

    Kept apart from Payment so a retry is a new attempt on the same payment
    and every provider answer can be reconciled. Only what's needed to match
    and audit is stored: no callback bodies, which carry the payer's number.
    """

    __tablename__ = "payment_transactions"
    __table_args__ = (
        UniqueConstraint(
            "checkout_request_id", name="uq_payment_transactions_checkout"
        ),
        UniqueConstraint("provider_receipt", name="uq_payment_transactions_receipt"),
        Index("ix_payment_transactions_status_requested", "status", "requested_at"),
    )

    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    merchant_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checkout_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PaymentTransactionStatus] = mapped_column(
        string_enum(PaymentTransactionStatus, name="payment_transaction_status"),
        nullable=False,
    )
    result_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Short reason category or provider description, never a phone number.
    result_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_receipt: Mapped[str | None] = mapped_column(String(32), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    payment: Mapped[Payment] = relationship()


class GymMpesaAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The gym's own M-Pesa Pay Bill or Till that members pay into.

    SWETO sends the STK Push on the gym's behalf with SWETO's Daraja app, so
    it needs the shortcode's Lipa na M-Pesa Online passkey. The passkey is
    stored encrypted and never returned by the API.
    """

    __tablename__ = "gym_mpesa_accounts"
    __table_args__ = (UniqueConstraint("gym_id", name="uq_gym_mpesa_accounts_gym"),)

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False
    )
    # paybill | till
    account_type: Mapped[str] = mapped_column(String(10), nullable=False)
    shortcode: Mapped[str] = mapped_column(String(10), nullable=False)
    # Till number for Buy Goods; the shortcode itself for Pay Bill.
    party_b: Mapped[str] = mapped_column(String(10), nullable=False)
    passkey_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    # The gym's own Daraja app (Safaricom binds an app to one shortcode).
    # Null on rows saved before this, which then use SWETO's app outside
    # production.
    consumer_key_encrypted: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    consumer_secret_encrypted: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
