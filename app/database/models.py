"""Import all database models so alembic can discover them"""

from app.modules.auth.models import AuthEvent, OTPChallenge, RefreshSession, User
from app.modules.gyms.models import (
    Amenity,
    Gym,
    GymAmenity,
    GymOperatingHours,
    GymStaff,
)
from app.modules.profiles.models import (
    UserAccountRole,
    UserProfile,
)

__all__ = [
    "Amenity",
    "AuthEvent",
    "Gym",
    "GymAmenity",
    "GymOperatingHours",
    "GymStaff",
    "OTPChallenge",
    "RefreshSession",
    "User",
    "UserAccountRole",
    "UserProfile",
]
