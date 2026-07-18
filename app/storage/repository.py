from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.enums import UploadStatus
from app.storage.models import StorageUpload


class StorageUploadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, upload: StorageUpload) -> None:
        self.session.add(upload)

    async def get_for_update(self, upload_id: UUID) -> StorageUpload | None:
        result = await self.session.execute(
            select(StorageUpload).where(StorageUpload.id == upload_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get(self, upload_id: UUID) -> StorageUpload | None:
        result = await self.session.execute(
            select(StorageUpload).where(StorageUpload.id == upload_id)
        )
        return result.scalar_one_or_none()

    async def list_expired_pending(self, now: datetime) -> list[StorageUpload]:
        result = await self.session.execute(
            select(StorageUpload).where(
                StorageUpload.status == UploadStatus.PENDING,
                StorageUpload.expires_at < now,
            )
        )
        return list(result.scalars().all())
