from app.modules.gyms.enums import GymVerificationDocumentType

REQUIRED_GYM_VERIFICATION_DOCUMENT_TYPES = frozenset(
    {
        GymVerificationDocumentType.BUSINESS_REGISTRATION,
        GymVerificationDocumentType.OWNER_IDENTIFICATION,
    }
)

ALLOWED_GYM_VERIFICATION_MIME_TYPES = frozenset(
    {"application/pdf", "image/jpeg", "image/png"}
)
MAX_GYM_VERIFICATION_FILE_SIZE_BYTES = 10 * 1024 * 1024
