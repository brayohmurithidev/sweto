from uuid import UUID

from app.modules.gyms.enums import GymVerificationDocumentType

ALLOWED_EXTENSION_BY_MIME_TYPE = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def build_gym_verification_key(
    *,
    gym_id: UUID,
    document_type: GymVerificationDocumentType,
    upload_id: UUID,
    mime_type: str,
) -> str:
    """Create a private, server-controlled key for a verification document."""

    extension = ALLOWED_EXTENSION_BY_MIME_TYPE[mime_type]
    return f"gyms/{gym_id}/verification/{document_type.value}/{upload_id}{extension}"
