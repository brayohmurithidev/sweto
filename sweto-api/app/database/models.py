"""Import all database models so alembic can discover them"""

from app.modules.auth.models import AuthEvent, OTPChallenge, RefreshSession, User
from app.modules.gyms.models import (
    Amenity,
    Gym,
    GymAmenity,
    GymOperatingHours,
    GymPhoto,
    GymStaff,
    GymVerificationDocument,
    GymVerificationReview,
)
from app.modules.members.models import (
    GymCheckIn,
    GymMember,
    GymMembership,
    MemberMessage,
    Payment,
    PaymentTransaction,
)
from app.modules.profiles.models import (
    UserAccountRole,
    UserProfile,
)
from app.storage.models import GymPhotoUpload, StorageUpload

__all__ = [
    "Amenity",
    "AuthEvent",
    "Gym",
    "GymAmenity",
    "GymCheckIn",
    "GymMember",
    "GymMembership",
    "GymOperatingHours",
    "GymPhoto",
    "GymStaff",
    "GymVerificationDocument",
    "GymVerificationReview",
    "MemberMessage",
    "OTPChallenge",
    "Payment",
    "PaymentTransaction",
    "RefreshSession",
    "User",
    "UserAccountRole",
    "UserProfile",
    "StorageUpload",
    "GymPhotoUpload",
]
