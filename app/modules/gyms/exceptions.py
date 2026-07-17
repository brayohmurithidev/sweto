class GymError(Exception):
    """Base exception for gym-related failures."""


class GymNotFoundError(GymError):
    """Raised when a requested gym cannot be found."""


class GymAccessDeniedError(GymError):
    """Raised when a user cannot access a gym."""


class GymSlugConflictError(GymError):
    """Raised when a unique gym slug cannot be generated."""


class GymAlreadyExistsError(GymError):
    """Raised when the owner already has a gym in the current workflow."""


class AmenityNotFoundError(GymError):
    """Raised when one or more selected amenities are invalid."""

class GymVerificationDocumentNotFoundError(Exception):
    """Raised when a verification document does not exist."""


class GymVerificationRequirementsError(Exception):
    """Raised when required verification documents are missing."""


class GymVerificationAlreadyPendingError(Exception):
    """Raised when verification is already under review."""


class GymVerificationReviewError(Exception):
    """Raised when a verification review cannot be completed."""

