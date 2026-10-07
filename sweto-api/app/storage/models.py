from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.types import string_enum
from app.modules.gyms.enums import GymVerificationDocumentType
from app.modules.gyms.photo_upload import GymPhotoUploadPurpose
from app.storage.enums import UploadPurpose, UploadStatus


class StorageUpload(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A short-lived intent for a client-direct private object upload."""

    __tablename__ = "storage_uploads"
    __table_args__ = (
        CheckConstraint(
            "declared_size_bytes > 0",
            name="storage_upload_declared_size_positive",
        ),
        CheckConstraint(
            "verified_size_bytes IS NULL OR verified_size_bytes > 0",
            name="storage_upload_verified_size_positive",
        ),
        CheckConstraint(
            "status != 'completed' OR "
            "(completed_at IS NOT NULL AND verified_mime_type IS NOT NULL "
            "AND verified_size_bytes IS NOT NULL)",
            name="storage_upload_completed_metadata_required",
        ),
    )

    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    purpose: Mapped[UploadPurpose] = mapped_column(
        string_enum(UploadPurpose, name="upload_purpose"), nullable=False, index=True
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[GymVerificationDocumentType] = mapped_column(
        string_enum(GymVerificationDocumentType, name="gym_verification_document_type"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(200), nullable=False)
    declared_mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    declared_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[UploadStatus] = mapped_column(
        string_enum(UploadStatus, name="upload_status"),
        nullable=False,
        index=True,
        default=UploadStatus.PENDING,
        server_default=UploadStatus.PENDING.value,
    )
    etag: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verified_mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class GymPhotoUpload(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pending direct-upload intent for a gym photo."""

    __tablename__ = "gym_photo_uploads"
    __table_args__ = (
        CheckConstraint(
            "declared_size_bytes > 0", name="gym_photo_upload_size_positive"
        ),
    )

    gym_id: Mapped[UUID] = mapped_column(
        ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[GymPhotoUploadPurpose] = mapped_column(
        string_enum(GymPhotoUploadPurpose, name="gym_photo_upload_purpose"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(200), nullable=False)
    declared_mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    declared_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[UploadStatus] = mapped_column(
        string_enum(UploadStatus, name="upload_status"),
        nullable=False,
        default=UploadStatus.PENDING,
        server_default=UploadStatus.PENDING.value,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
