from uuid import UUID

from app.modules.gyms.enums import GymVerificationDocumentType

ALLOWED_EXTENSION_BY_MIME_TYPE = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

ALLOWED_GYM_PHOTO_EXTENSION_BY_MIME_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def build_gym_photo_key(*, gym_id: UUID, upload_id: UUID, mime_type: str) -> str:
    extension = ALLOWED_GYM_PHOTO_EXTENSION_BY_MIME_TYPE[mime_type]
    return f"gyms/{gym_id}/photos/{upload_id}{extension}"


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
