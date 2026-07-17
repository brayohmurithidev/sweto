from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.modules.gyms.enums import (
    DayOfWeek,
    GymBusinessType,
    GymOnboardingStep,
    GymStatus,
    GymVerificationDocumentType,
    GymVerificationReviewDecision,
    GymVerificationStatus,
    GymVerificationStatus,
    MembershipBillingPeriod,
)


class CreateGymRequest(BaseModel):
    """Initial gym registration details."""

    name: str = Field(
        min_length=2,
        max_length=180,
        examples=["FlexFit Westlands"],
    )

    phone_number: str | None = Field(
        default=None,
        min_length=7,
        max_length=30,
    )

    email: EmailStr | None = None

    description: str | None = Field(
        default=None,
        max_length=3000,
    )


class GymData(BaseModel):
    """Gym information returned to the mobile application."""

    id: UUID
    name: str
    slug: str

    description: str | None
    phone_number: str | None
    email: EmailStr | None

    legal_business_name: str | None
    business_type: GymBusinessType | None
    registration_number: str | None
    tax_number: str | None
    contact_person_name: str | None
    contact_person_phone: str | None

    address_line: str | None
    neighbourhood: str | None
    city: str | None
    country_code: str

    latitude: Decimal | None
    longitude: Decimal | None

    logo_url: str | None
    cover_photo_url: str | None

    status: GymStatus
    verification_status: GymVerificationStatus
    onboarding_step: GymOnboardingStep
    onboarding_completed: bool
    is_listed: bool

    created_at: datetime
    updated_at: datetime


class GymOnboardingData(BaseModel):
    """Current gym onboarding state."""

    gym_id: UUID
    status: GymStatus
    verification_status: GymVerificationStatus
    onboarding_step: GymOnboardingStep
    onboarding_completed: bool
    next_step: str
    limited_access: bool


class CreateGymData(BaseModel):
    """Result returned after registering a gym."""

    gym: GymData
    onboarding: GymOnboardingData


class UpdateGymLocationRequest(BaseModel):
    """Location details collected during gym onboarding."""

    address_line: str = Field(
        min_length=3,
        max_length=300,
        examples=["ABC Place, Waiyaki Way"],
    )

    neighbourhood: str = Field(
        min_length=2,
        max_length=120,
        examples=["Westlands"],
    )

    city: str = Field(
        min_length=2,
        max_length=120,
        examples=["Nairobi"],
    )

    country_code: str = Field(
        default="KE",
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z]{2}$",
    )

    latitude: Decimal = Field(
        ge=Decimal("-90"),
        le=Decimal("90"),
        examples=[Decimal("-1.2676")],
    )

    longitude: Decimal = Field(
        ge=Decimal("-180"),
        le=Decimal("180"),
        examples=[Decimal("36.8108")],
    )


class UpdateGymLocationData(BaseModel):
    """Result returned after saving gym location details."""

    gym: GymData
    onboarding: GymOnboardingData


class UpdateGymBusinessDetailsRequest(BaseModel):
    """Business details collected during gym onboarding."""

    legal_business_name: str = Field(
        min_length=2,
        max_length=200,
        examples=["FlexFit Wellness Limited"],
    )

    business_type: GymBusinessType

    registration_number: str = Field(
        min_length=2,
        max_length=100,
        examples=["PVT-ABC123"],
    )

    tax_number: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        examples=["A012345678B"],
    )

    contact_person_name: str = Field(
        min_length=2,
        max_length=150,
        examples=["Brian Murithi"],
    )

    contact_person_phone: str = Field(
        min_length=7,
        max_length=30,
        examples=["+254712345678"],
    )


class UpdateGymBusinessDetailsData(BaseModel):
    """Result returned after saving gym business details."""

    gym: GymData
    onboarding: GymOnboardingData


class AmenityData(BaseModel):
    """Amenity available for gym selection."""

    id: UUID
    name: str
    slug: str
    description: str | None
    icon: str | None
    display_order: int


class UpdateGymAmenitiesRequest(BaseModel):
    """Amenities selected by a gym."""

    amenity_ids: list[UUID] = Field(
        default_factory=list,
        max_length=100,
    )


class UpdateGymAmenitiesData(BaseModel):
    """Result returned after replacing gym amenities."""

    gym_id: UUID
    amenities: list[AmenityData]
    onboarding: GymOnboardingData


class GymOperatingHoursInput(BaseModel):
    """Operating schedule for one day."""

    day_of_week: DayOfWeek
    is_closed: bool = False
    is_24_hours: bool = False
    opens_at: time | None = None
    closes_at: time | None = None

    @model_validator(mode="after")
    def validate_schedule(
        self,
    ) -> "GymOperatingHoursInput":
        if self.is_closed and self.is_24_hours:
            raise ValueError("A day cannot be both closed and open for 24 hours.")

        if self.is_closed:
            if self.opens_at is not None or self.closes_at is not None:
                raise ValueError(
                    "Closed days must not include opening or closing times."
                )

            return self

        if self.is_24_hours:
            if self.opens_at is not None or self.closes_at is not None:
                raise ValueError(
                    "A 24-hour day must not include opening or closing times."
                )

            return self

        if self.opens_at is None or self.closes_at is None:
            raise ValueError("Opening and closing times are required for an open day.")

        if self.opens_at == self.closes_at:
            raise ValueError("Opening and closing times cannot be the same.")

        return self


class UpdateGymOperatingHoursRequest(BaseModel):
    """Complete seven-day operating schedule."""

    operating_hours: list[GymOperatingHoursInput] = Field(
        min_length=7,
        max_length=7,
    )

    @model_validator(mode="after")
    def validate_complete_week(
        self,
    ) -> "UpdateGymOperatingHoursRequest":
        submitted_days = {schedule.day_of_week for schedule in self.operating_hours}

        expected_days = set(DayOfWeek)

        if submitted_days != expected_days:
            missing_days = sorted(
                day.name.lower() for day in expected_days - submitted_days
            )

            duplicate_or_invalid = len(submitted_days) != len(self.operating_hours)

            if duplicate_or_invalid:
                raise ValueError("Each day of the week must appear exactly once.")

            raise ValueError(
                "Operating hours are missing days: " + ", ".join(missing_days)
            )

        return self


class GymOperatingHoursData(BaseModel):
    """Saved operating schedule for one day."""

    id: UUID
    day_of_week: DayOfWeek
    is_closed: bool
    is_24_hours: bool
    opens_at: time | None
    closes_at: time | None


class UpdateGymOperatingHoursData(BaseModel):
    """Result returned after saving operating hours."""

    gym_id: UUID
    operating_hours: list[GymOperatingHoursData]
    onboarding: GymOnboardingData


class GymDayPassInput(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=120,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str = Field(
        default="KES",
        min_length=3,
        max_length=3,
    )
    validity_hours: int = Field(
        default=24,
        ge=1,
        le=720,
    )
    is_active: bool = True
    display_order: int = Field(
        default=0,
        ge=0,
    )

    @field_validator("name")
    @classmethod
    def normalize_name(
        cls,
        value: str,
    ) -> str:
        return " ".join(value.split())

    @field_validator("currency")
    @classmethod
    def normalize_currency(
        cls,
        value: str,
    ) -> str:
        return value.strip().upper()


class GymMembershipBenefitInput(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=200,
    )
    display_order: int = Field(
        default=0,
        ge=0,
    )

    @field_validator("name")
    @classmethod
    def normalize_name(
        cls,
        value: str,
    ) -> str:
        return " ".join(value.split())


class GymMembershipPlanInput(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=120,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str = Field(
        default="KES",
        min_length=3,
        max_length=3,
    )
    billing_period: MembershipBillingPeriod
    access_days: int | None = Field(
        default=None,
        ge=1,
        le=366,
    )
    visit_limit: int | None = Field(
        default=None,
        ge=1,
    )
    is_active: bool = True
    is_featured: bool = False
    display_order: int = Field(
        default=0,
        ge=0,
    )
    benefits: list[GymMembershipBenefitInput] = Field(
        default_factory=list,
        max_length=20,
    )

    @field_validator("name")
    @classmethod
    def normalize_name(
        cls,
        value: str,
    ) -> str:
        return " ".join(value.split())

    @field_validator("currency")
    @classmethod
    def normalize_currency(
        cls,
        value: str,
    ) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_unique_benefits(
        self,
    ) -> "GymMembershipPlanInput":
        normalized_names = [benefit.name.casefold() for benefit in self.benefits]

        if len(normalized_names) != len(set(normalized_names)):
            raise ValueError("A membership plan cannot contain duplicate benefits.")

        return self


class UpdateGymPricingRequest(BaseModel):
    day_passes: list[GymDayPassInput] = Field(
        default_factory=list,
        max_length=20,
    )
    membership_plans: list[GymMembershipPlanInput] = Field(
        default_factory=list,
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_pricing_options(
        self,
    ) -> "UpdateGymPricingRequest":
        if not self.day_passes and not self.membership_plans:
            raise ValueError("Provide at least one day pass or membership plan.")

        day_pass_names = [day_pass.name.casefold() for day_pass in self.day_passes]

        if len(day_pass_names) != len(set(day_pass_names)):
            raise ValueError("Day-pass names must be unique.")

        membership_names = [plan.name.casefold() for plan in self.membership_plans]

        if len(membership_names) != len(set(membership_names)):
            raise ValueError("Membership-plan names must be unique.")

        featured_count = sum(plan.is_featured for plan in self.membership_plans)

        if featured_count > 1:
            raise ValueError("Only one membership plan can be featured.")

        currencies = {day_pass.currency for day_pass in self.day_passes} | {
            plan.currency for plan in self.membership_plans
        }

        if len(currencies) > 1:
            raise ValueError("All gym pricing options must use the same currency.")

        return self


class GymMembershipBenefitData(BaseModel):
    id: UUID
    name: str
    display_order: int


class GymDayPassData(BaseModel):
    id: UUID
    name: str
    description: str | None
    amount: Decimal
    currency: str
    validity_hours: int
    is_active: bool
    display_order: int


class GymMembershipPlanData(BaseModel):
    id: UUID
    name: str
    description: str | None
    amount: Decimal
    currency: str
    billing_period: MembershipBillingPeriod
    access_days: int | None
    visit_limit: int | None
    is_active: bool
    is_featured: bool
    display_order: int
    benefits: list[GymMembershipBenefitData]


class GymPricingData(BaseModel):
    gym_id: UUID
    day_passes: list[GymDayPassData]
    membership_plans: list[GymMembershipPlanData]


class UpdateGymPricingData(GymPricingData):
    onboarding: GymOnboardingData


class CreateGymVerificationDocumentRequest(BaseModel):
    document_type: GymVerificationDocumentType
    document_name: str = Field(
        min_length=2,
        max_length=200,
    )
    storage_key: str = Field(
        min_length=3,
        max_length=500,
    )
    file_url: str | None = Field(
        default=None,
        max_length=1000,
    )
    mime_type: str = Field(
        min_length=3,
        max_length=100,
    )
    file_size_bytes: int = Field(
        gt=0,
        le=10 * 1024 * 1024,
    )


class GymVerificationDocumentData(BaseModel):
    id: UUID
    document_type: GymVerificationDocumentType
    document_name: str
    storage_key: str
    file_url: str | None
    mime_type: str
    file_size_bytes: int
    is_active: bool
    uploaded_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class GymVerificationData(BaseModel):
    gym_id: UUID
    verification_status: GymVerificationStatus
    submitted_at: datetime | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    documents: list[GymVerificationDocumentData]
    onboarding: GymOnboardingData


class SubmitGymVerificationRequest(BaseModel):
    confirmation: bool

    @model_validator(mode="after")
    def validate_confirmation(
        self,
    ) -> "SubmitGymVerificationRequest":
        if not self.confirmation:
            raise ValueError(
                "Verification submission must be confirmed."
            )

        return self
    

class ReviewGymVerificationRequest(BaseModel):
    decision: GymVerificationReviewDecision
    notes: str | None = Field(
        default=None,
        max_length=2000,
    )
    rejection_reason: str | None = Field(
        default=None,
        max_length=2000,
    )

    @model_validator(mode="after")
    def validate_review(
        self,
    ) -> "ReviewGymVerificationRequest":
        if (
            self.decision
            == GymVerificationReviewDecision.REJECT
            and not self.rejection_reason
        ):
            raise ValueError(
                "A rejection reason is required."
            )

        if (
            self.decision
            == GymVerificationReviewDecision.APPROVE
            and self.rejection_reason is not None
        ):
            raise ValueError(
                "An approved verification cannot have a "
                "rejection reason."
            )

        return self
    

class GymVerificationReviewData(BaseModel):
    id: UUID
    gym_id: UUID
    decision: GymVerificationReviewDecision
    notes: str | None
    rejection_reason: str | None
    reviewed_by_user_id: UUID
    reviewed_at: datetime
    onboarding: GymOnboardingData