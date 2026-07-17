from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.profiles.enums import (
    AccountRole,
    Gender,
    OnboardingStatus,
)


class SelectAccountRoleRequest(BaseModel):
    """Request body for selecting an account experience."""

    role: AccountRole


class AccountRoleData(BaseModel):
    """One account role assigned to a user."""

    id: UUID
    role: AccountRole
    is_active: bool
    is_default: bool


class AccountSetupData(BaseModel):
    """Account setup state returned to the mobile app."""

    roles: list[AccountRoleData]
    default_role: AccountRole | None
    onboarding_status: OnboardingStatus
    onboarding_completed: bool
    next_step: str


class OnboardingStatusData(BaseModel):
    """Current onboarding state for the authenticated user."""

    roles: list[AccountRole]
    default_role: AccountRole | None
    onboarding_status: OnboardingStatus
    onboarding_completed: bool
    next_step: str


class ProfileData(BaseModel):
    """Personal profile returned to the mobile application."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    phone_number: str

    full_name: str | None
    email: EmailStr | None
    avatar_url: str | None

    neighbourhood: str | None
    city: str | None
    country_code: str

    gender: Gender | None
    date_of_birth: date | None

    onboarding_status: OnboardingStatus
    onboarding_completed: bool

    created_at: datetime
    updated_at: datetime


class UpdateProfileRequest(BaseModel):
    """Fields that may be updated on a SWETO personal profile."""

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    email: EmailStr | None = None

    avatar_url: str | None = Field(
        default=None,
        max_length=1000,
    )

    neighbourhood: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )

    city: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )

    country_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z]{2}$",
    )

    gender: Gender | None = None

    date_of_birth: date | None = None


class UpdateProfileData(BaseModel):
    """Result returned after updating a personal profile."""

    profile: ProfileData
    next_step: str
