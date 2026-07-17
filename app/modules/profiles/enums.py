from enum import StrEnum


class AccountRole(StrEnum):
    """Account experiences available to SWETO user"""

    MEMBER = "member"
    GYM_OWNER = "gym_owner"


class OnboardingStatus(StrEnum):
    """Overall onboarding progress for a SWETO user."""

    ACCOUNT_SELECTION_PENDING = "account_selection_pending"
    PROFILE_SETUP_PENDING = "profile_setup_pending"
    GYM_SETUP_PENDING = "gym_setup_pending"
    VERIFICATION_PENDING = "verification_pending"
    COMPLETED = "completed"


class Gender(StrEnum):
    """Optional gender values supported in a user profile."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"
