from enum import StrEnum


class UploadStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class UploadPurpose(StrEnum):
    GYM_VERIFICATION_DOCUMENT = "gym_verification_document"
