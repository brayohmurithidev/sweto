from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.database.types import string_enum
from app.modules.auth.enums import (
    AuthEventOutcome,
    AuthEventType,
    OTPDeliveryChannel,
    OTPDeliveryStatus,
    OTPPurpose,
    OTPStatus,
    SessionStatus,
    UserRole,
    UserStatus,
)

if TYPE_CHECKING:
    from app.modules.gyms.models import GymStaff
    from app.modules.profiles.models import (
        UserAccountRole,
        UserProfile,
    )


class User(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """A person who can authenticate with SWETO."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'admin', 'super_admin')",
            name="user_role_valid",
        ),
        CheckConstraint(
            "phone_number IS NOT NULL OR email IS NOT NULL",
            name="login_identity_required",
        ),
        CheckConstraint(
            "role NOT IN ('admin', 'super_admin') "
            "OR (email IS NOT NULL AND password_hash IS NOT NULL)",
            name="administrative_credentials_required",
        ),
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        unique=True,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[UserRole] = mapped_column(
        string_enum(
            UserRole,
            name="user_role",
        ),
        nullable=False,
        index=True,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )

    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    is_system_protected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    status: Mapped[UserStatus] = mapped_column(
        string_enum(
            UserStatus,
            name="user_status",
        ),
        nullable=False,
        default=UserStatus.PENDING,
        server_default=UserStatus.PENDING.value,
    )

    is_phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    account_roles: Mapped[list["UserAccountRole"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    gym_staff_memberships: Mapped[list["GymStaff"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class OTPChallenge(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """A short-lived one-time-password verification challenge."""

    __tablename__ = "otp_challenges"
    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0",
            name="attempt_count_non_negative",
        ),
        CheckConstraint(
            "max_attempts > 0",
            name="max_attempts_positive",
        ),
        Index(
            "ix_otp_challenges_phone_purpose_status",
            "phone_number",
            "purpose",
            "status",
        ),
        # At most one usable code per number and purpose, even when two
        # requests race each other.
        Index(
            "uq_otp_challenges_one_pending",
            "phone_number",
            "purpose",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    phone_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    purpose: Mapped[OTPPurpose] = mapped_column(
        string_enum(
            OTPPurpose,
            name="otp_purpose",
        ),
        nullable=False,
    )

    status: Mapped[OTPStatus] = mapped_column(
        string_enum(
            OTPStatus,
            name="otp_status",
        ),
        nullable=False,
        default=OTPStatus.PENDING,
        server_default=OTPStatus.PENDING.value,
    )

    delivery_channel: Mapped[OTPDeliveryChannel] = mapped_column(
        string_enum(
            OTPDeliveryChannel,
            name="otp_delivery_channel",
        ),
        nullable=False,
        default=OTPDeliveryChannel.SMS,
        server_default=OTPDeliveryChannel.SMS.value,
    )

    # Provider message ID (for example a WhatsApp "wamid"), used to match
    # delivery reports to this challenge.
    provider_message_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
    )

    delivery_status: Mapped[OTPDeliveryStatus] = mapped_column(
        string_enum(
            OTPDeliveryStatus,
            name="otp_delivery_status",
        ),
        nullable=False,
        default=OTPDeliveryStatus.PENDING,
        server_default=OTPDeliveryStatus.PENDING.value,
    )

    delivery_status_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Provider error code when delivery failed (never the provider message).
    delivery_error_code: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    code_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )

    requested_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class RefreshSession(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """An authenticated refresh-token session for one device."""

    __tablename__ = "refresh_sessions"
    __table_args__ = (
        Index(
            "ix_refresh_sessions_user_status",
            "user_id",
            "status",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    status: Mapped[SessionStatus] = mapped_column(
        string_enum(
            SessionStatus,
            name="session_status",
        ),
        nullable=False,
        default=SessionStatus.ACTIVE,
        server_default=SessionStatus.ACTIVE.value,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    device_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    device_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    platform: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    user: Mapped[User] = relationship(
        back_populates="refresh_sessions",
    )


class AuthEvent(
    UUIDPrimaryKeyMixin,
    Base,
):
    """An immutable security event generated by authentication workflows."""

    __tablename__ = "auth_events"
    __table_args__ = (
        Index(
            "ix_auth_events_user_created_at",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_auth_events_phone_created_at",
            "phone_number",
            "created_at",
        ),
        Index(
            "ix_auth_events_type_created_at",
            "event_type",
            "created_at",
        ),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "refresh_sessions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    challenge_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "otp_challenges.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    event_type: Mapped[AuthEventType] = mapped_column(
        string_enum(
            AuthEventType,
            name="auth_event_type",
        ),
        nullable=False,
    )

    outcome: Mapped[AuthEventOutcome] = mapped_column(
        string_enum(
            AuthEventOutcome,
            name="auth_event_outcome",
        ),
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
