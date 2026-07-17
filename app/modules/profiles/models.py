from datetime import date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.database.types import string_enum
from app.modules.auth.models import User
from app.modules.profiles.enums import (
    AccountRole,
    Gender,
    OnboardingStatus,
)


class UserProfile(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """Personal profile attached to an authenticated SWETO user."""

    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    neighbourhood: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        default="KE",
        server_default="KE",
    )

    gender: Mapped[Gender | None] = mapped_column(
        string_enum(
            Gender,
            name="profile_gender",
        ),
        nullable=True,
    )

    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    onboarding_status: Mapped[OnboardingStatus] = mapped_column(
        string_enum(
            OnboardingStatus,
            name="onboarding_status",
        ),
        nullable=False,
        default=OnboardingStatus.ACCOUNT_SELECTION_PENDING,
        server_default=(OnboardingStatus.ACCOUNT_SELECTION_PENDING.value),
    )

    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    user: Mapped[User] = relationship(
        back_populates="profile",
    )


class UserAccountRole(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """An account experience enabled for a SWETO user."""

    __tablename__ = "user_account_roles"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "role",
            name="uq_user_account_roles_user_role",
        ),
        Index(
            "ix_user_account_roles_user_active",
            "user_id",
            "is_active",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    role: Mapped[AccountRole] = mapped_column(
        string_enum(
            AccountRole,
            name="account_role",
        ),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    user: Mapped[User] = relationship(
        back_populates="account_roles",
    )
