class GymError(Exception):
    """Base exception for gym-related failures."""


class GymPhotoUploadInvalidError(GymError):
    """Raised when gym-photo upload metadata is invalid."""


class GymPhotoLimitReachedError(GymError):
    """Raised when a gym has reached its active photo limit."""


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


class GymVerificationDocumentNotFoundError(GymError):
    """Raised when a verification document does not exist."""


class GymVerificationDocumentInvalidError(GymError):
    """Raised when verification document metadata is invalid."""


class GymVerificationRequirementsError(GymError):
    """Raised when required verification documents are missing."""

    def __init__(self, missing_document_types: list[str]) -> None:
        self.missing_document_types = missing_document_types
        super().__init__(
            "Missing required documents: " + ", ".join(missing_document_types) + "."
        )


class GymVerificationAlreadyPendingError(GymError):
    """Raised when verification is already under review."""


class GymVerificationAlreadyApprovedError(GymError):
    """Raised when an approved gym is submitted or edited."""


class GymVerificationReviewInProgressError(GymError):
    """Raised when pending verification metadata would be changed."""


class GymVerificationNotPendingError(GymError):
    """Raised when a verification review cannot be completed."""


class GymVerificationRejectionReasonRequiredError(GymError):
    """Raised when a rejection has no usable reason."""


class GymVerificationAccessDeniedError(GymError):
    """Raised when a user cannot access a gym verification submission."""
