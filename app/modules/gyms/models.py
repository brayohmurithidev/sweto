from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.database.types import string_enum
from app.modules.gyms.enums import (
    DayOfWeek,
    GymBusinessType,
    GymOnboardingStep,
    GymStaffRole,
    GymStaffStatus,
    GymStatus,
    GymVerificationDecision,
    GymVerificationDocumentType,
    GymVerificationStatus,
    MembershipBillingPeriod,
)

if TYPE_CHECKING:
    from app.modules.auth.models import User


class Gym(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """A fitness business registered on SWETO."""

    __tablename__ = "gyms"
    __table_args__ = (
        Index(
            "ix_gyms_city_neighbourhood",
            "city",
            "neighbourhood",
        ),
        Index(
            "ix_gyms_status_verification",
            "status",
            "verification_status",
        ),
        Index(
            "ix_gyms_verification_status_submitted_at",
            "verification_status",
            "verification_submitted_at",
        ),
        CheckConstraint(
            "verification_status IN "
            "('not_submitted', 'pending', 'approved', 'rejected')",
            name="gym_verification_status_valid",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(220),
        nullable=False,
        unique=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    legal_business_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    business_type: Mapped[GymBusinessType | None] = mapped_column(
        string_enum(
            GymBusinessType,
            name="gym_business_type",
        ),
        nullable=True,
    )

    registration_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tax_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    contact_person_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    contact_person_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    address_line: Mapped[str | None] = mapped_column(
        String(300),
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

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=10,
            scale=7,
        ),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=10,
            scale=7,
        ),
        nullable=True,
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    cover_photo_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    status: Mapped[GymStatus] = mapped_column(
        string_enum(
            GymStatus,
            name="gym_status",
        ),
        nullable=False,
        default=GymStatus.DRAFT,
        server_default=GymStatus.DRAFT.value,
    )

    verification_status: Mapped[GymVerificationStatus] = mapped_column(
        string_enum(
            GymVerificationStatus,
            name="gym_verification_status",
        ),
        nullable=False,
        default=GymVerificationStatus.NOT_SUBMITTED,
        server_default=GymVerificationStatus.NOT_SUBMITTED.value,
    )

    onboarding_step: Mapped[GymOnboardingStep] = mapped_column(
        string_enum(
            GymOnboardingStep,
            name="gym_onboarding_step",
        ),
        nullable=False,
        default=GymOnboardingStep.BASIC_INFORMATION,
        server_default=GymOnboardingStep.BASIC_INFORMATION.value,
    )

    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    is_listed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    verification_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verification_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verification_rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    staff_members: Mapped[list["GymStaff"]] = relationship(
        back_populates="gym",
        cascade="all, delete-orphan",
    )

    operating_hours: Mapped[list["GymOperatingHours"]] = relationship(
        back_populates="gym",
        cascade="all, delete-orphan",
    )

    amenity_links: Mapped[list["GymAmenity"]] = relationship(
        back_populates="gym",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    day_passes: Mapped[list["GymDayPass"]] = relationship(
        back_populates="gym",
        cascade="all, delete-orphan",
        order_by="GymDayPass.display_order",
    )

    membership_plans: Mapped[list["GymMembershipPlan"]] = relationship(
        back_populates="gym",
        cascade="all, delete-orphan",
        order_by="GymMembershipPlan.display_order",
    )

    verification_documents: Mapped[list["GymVerificationDocument"]] = relationship(
        back_populates="gym",
        cascade="all, delete-orphan",
    )

    verification_reviews: Mapped[list["GymVerificationReview"]] = relationship(
        back_populates="gym",
        cascade="all, delete-orphan",
        order_by="GymVerificationReview.reviewed_at.asc()",
    )


class GymStaff(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """A user's role and access within a gym."""

    __tablename__ = "gym_staff"
    __table_args__ = (
        UniqueConstraint(
            "gym_id",
            "user_id",
            name="uq_gym_staff_gym_user",
        ),
        Index(
            "ix_gym_staff_user_status",
            "user_id",
            "status",
        ),
        Index(
            "ix_gym_staff_gym_role_status",
            "gym_id",
            "role",
            "status",
        ),
    )

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "gyms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    role: Mapped[GymStaffRole] = mapped_column(
        string_enum(
            GymStaffRole,
            name="gym_staff_role",
        ),
        nullable=False,
    )

    status: Mapped[GymStaffStatus] = mapped_column(
        string_enum(
            GymStaffStatus,
            name="gym_staff_status",
        ),
        nullable=False,
        default=GymStaffStatus.ACTIVE,
        server_default=GymStaffStatus.ACTIVE.value,
    )

    is_primary_owner: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    gym: Mapped[Gym] = relationship(
        back_populates="staff_members",
    )

    user: Mapped["User"] = relationship(
        back_populates="gym_staff_memberships",
    )


class GymOperatingHours(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """Opening and closing hours for one day of the week."""

    __tablename__ = "gym_operating_hours"
    __table_args__ = (
        UniqueConstraint(
            "gym_id",
            "day_of_week",
            name="uq_gym_operating_hours_gym_day",
        ),
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="ck_gym_operating_hours_day_of_week_valid",
        ),
        CheckConstraint(
            """
    (
        is_closed = true
        AND is_24_hours = false
        AND opens_at IS NULL
        AND closes_at IS NULL
    )
    OR
    (
        is_closed = false
        AND is_24_hours = true
        AND opens_at IS NULL
        AND closes_at IS NULL
    )
    OR
    (
        is_closed = false
        AND is_24_hours = false
        AND opens_at IS NOT NULL
        AND closes_at IS NOT NULL
        AND opens_at <> closes_at
    )
    """,
            name="ck_gym_operating_hours_valid_schedule",
        ),
    )

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "gyms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    day_of_week: Mapped[DayOfWeek] = mapped_column(
        Integer,
        nullable=False,
    )

    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    opens_at: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    closes_at: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )
    is_24_hours: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )

    gym: Mapped[Gym] = relationship(
        back_populates="operating_hours",
    )


class Amenity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reusable amenity available for selection by gyms."""

    __tablename__ = "amenities"

    __table_args__ = (
        UniqueConstraint(
            "slug",
            name="uq_amenities_slug",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(140),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(
        default=0,
        server_default="0",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        nullable=False,
    )

    gym_links: Mapped[list["GymAmenity"]] = relationship(
        back_populates="amenity",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class GymAmenity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Association between a gym and a supported amenity."""

    __tablename__ = "gym_amenities"

    __table_args__ = (
        UniqueConstraint(
            "gym_id",
            "amenity_id",
            name="uq_gym_amenities_gym_amenity",
        ),
    )

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "gyms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    amenity_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "amenities.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    gym: Mapped["Gym"] = relationship(
        back_populates="amenity_links",
    )

    amenity: Mapped["Amenity"] = relationship(
        back_populates="gym_links",
    )


class GymDayPass(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One-time gym-access option."""

    __tablename__ = "gym_day_passes"

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "gyms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="KES",
        server_default="KES",
        nullable=False,
    )

    validity_hours: Mapped[int] = mapped_column(
        Integer,
        default=24,
        server_default="24",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    gym: Mapped["Gym"] = relationship(
        back_populates="day_passes",
    )

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_gym_day_passes_amount_positive",
        ),
        CheckConstraint(
            "validity_hours > 0",
            name="ck_gym_day_passes_validity_positive",
        ),
        CheckConstraint(
            "char_length(currency) = 3",
            name="ck_gym_day_passes_currency_length",
        ),
        UniqueConstraint(
            "gym_id",
            "name",
            name="uq_gym_day_passes_gym_name",
        ),
    )


class GymMembershipPlan(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
):
    """Recurring or fixed-period gym membership."""

    __tablename__ = "gym_membership_plans"

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "gyms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="KES",
        server_default="KES",
        nullable=False,
    )

    billing_period: Mapped[MembershipBillingPeriod] = mapped_column(
        String(30),
        nullable=False,
    )

    access_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    visit_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    gym: Mapped["Gym"] = relationship(
        back_populates="membership_plans",
    )

    benefits: Mapped[list["GymMembershipPlanBenefit"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="GymMembershipPlanBenefit.display_order",
    )

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_gym_membership_plans_amount_positive",
        ),
        CheckConstraint(
            "access_days IS NULL OR access_days > 0",
            name="ck_gym_membership_plans_access_days_positive",
        ),
        CheckConstraint(
            "visit_limit IS NULL OR visit_limit > 0",
            name="ck_gym_membership_plans_visit_limit_positive",
        ),
        CheckConstraint(
            "char_length(currency) = 3",
            name="ck_gym_membership_plans_currency_length",
        ),
        UniqueConstraint(
            "gym_id",
            "name",
            name="uq_gym_membership_plans_gym_name",
        ),
    )


class GymMembershipPlanBenefit(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
):
    """Benefit displayed under a membership plan."""

    __tablename__ = "gym_membership_plan_benefits"

    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "gym_membership_plans.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    plan: Mapped["GymMembershipPlan"] = relationship(
        back_populates="benefits",
    )

    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "name",
            name="uq_gym_membership_plan_benefits_plan_name",
        ),
    )


class GymVerificationDocument(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
):
    """Document uploaded for gym verification."""

    __tablename__ = "gym_verification_documents"

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "gyms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    document_type: Mapped[GymVerificationDocumentType] = mapped_column(
        string_enum(
            GymVerificationDocumentType,
            name="gym_verification_document_type",
        ),
        nullable=False,
    )

    document_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    storage_bucket: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    file_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    etag: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    gym: Mapped["Gym"] = relationship(
        back_populates="verification_documents",
    )

    __table_args__ = (
        CheckConstraint(
            "file_size_bytes > 0",
            name=("ck_gym_verification_documents_file_size_positive"),
        ),
        UniqueConstraint(
            "gym_id",
            "document_type",
            name=("uq_gym_verification_documents_gym_document_type"),
        ),
    )


class GymVerificationReview(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
):
    """Administrative review of a gym verification submission."""

    __tablename__ = "gym_verification_reviews"

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "gyms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    reviewed_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    decision: Mapped[GymVerificationDecision] = mapped_column(
        string_enum(
            GymVerificationDecision,
            name="gym_verification_decision",
        ),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    gym: Mapped["Gym"] = relationship(
        back_populates="verification_reviews",
    )

    __table_args__ = (
        Index(
            "ix_gym_verification_reviews_gym_reviewed_at",
            "gym_id",
            "reviewed_at",
        ),
        CheckConstraint(
            "decision IN ('approve', 'reject')",
            name=("ck_gym_verification_reviews_decision_valid"),
        ),
        CheckConstraint(
            """
            (decision = 'approve' AND rejection_reason IS NULL)
            OR (
                decision = 'reject'
                AND rejection_reason IS NOT NULL
                AND char_length(trim(rejection_reason)) > 0
            )
            """,
            name=("ck_gym_verification_reviews_rejection_reason_required"),
        ),
    )
