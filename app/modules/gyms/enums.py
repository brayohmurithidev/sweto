from enum import IntEnum, StrEnum


class GymStatus(StrEnum):
    """Operational state of a gym listing."""

    DRAFT = "draft"
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"
    DEACTIVATED = "deactivated"


class GymVerificationStatus(StrEnum):
    """Verification state of a gym business."""

    NOT_SUBMITTED = "not_submitted"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GymOnboardingStep(StrEnum):
    """Current step in the gym registration workflow."""

    BASIC_INFORMATION = "basic_information"
    LOCATION = "location"
    BUSINESS_DETAILS = "business_details"
    AMENITIES = "amenities"
    OPERATING_HOURS = "operating_hours"
    PRICING = "pricing"
    VERIFICATION = "verification"
    COMPLETED = "completed"


class GymStaffRole(StrEnum):
    """Role held by a user within a gym."""

    OWNER = "owner"
    MANAGER = "manager"
    RECEPTIONIST = "receptionist"
    TRAINER = "trainer"


class GymStaffStatus(StrEnum):
    """Access status of a gym staff relationship."""

    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class GymBusinessType(StrEnum):
    """Legal or operational structure of a gym business."""

    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    PARTNERSHIP = "partnership"
    LIMITED_COMPANY = "limited_company"
    NON_PROFIT = "non_profit"
    OTHER = "other"


class DayOfWeek(IntEnum):
    """ISO-style day numbering used for gym operating hours."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class MembershipBillingPeriod(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class GymVerificationDocumentType(StrEnum):
    BUSINESS_REGISTRATION = "business_registration"
    OWNER_IDENTIFICATION = "owner_identification"
    TAX_CERTIFICATE = "tax_certificate"
    OPERATING_LICENSE = "operating_license"
    PROOF_OF_ADDRESS = "proof_of_address"
    OTHER = "other"


class GymVerificationDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
