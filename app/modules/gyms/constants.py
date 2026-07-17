from app.modules.gyms.enums import GymVerificationDocumentType


REQUIRED_VERIFICATION_DOCUMENT_TYPES = frozenset(
    {
        GymVerificationDocumentType.BUSINESS_REGISTRATION,
        GymVerificationDocumentType.OWNER_IDENTIFICATION,
    }
)
