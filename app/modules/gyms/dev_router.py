"""Development-only helpers for exercising private S3 upload flows."""

from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.gyms.constants import MAX_GYM_VERIFICATION_FILE_SIZE_BYTES
from app.modules.gyms.enums import GymVerificationDocumentType
from app.modules.gyms.exceptions import GymVerificationDocumentInvalidError
from app.modules.gyms.schemas import (
    DevelopmentVerificationUploadData,
    GymVerificationUploadRequest,
)
from app.modules.gyms.service import GymService
from app.shared.responses import APIResponse
from app.storage.exceptions import StorageUploadFailedError
from app.storage.s3 import S3Storage

router = APIRouter(prefix="/dev/gyms", tags=["Development gym uploads"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
ApplicationSettings = Annotated[Settings, Depends(get_settings)]
_CHUNK_SIZE_BYTES = 1024 * 1024


@router.post(
    "/{gym_id}/verification/documents/{document_type}/upload",
    response_model=APIResponse[DevelopmentVerificationUploadData],
    summary="Development-only direct S3 verification upload",
    description=(
        "Available only in local, development, and testing. It proxies a file through "
        "the same initiate → presigned PUT → complete flow. Production clients must "
        "upload directly using the regular initiate and completion endpoints."
    ),
)
async def development_upload_verification_document(
    gym_id: UUID,
    document_type: GymVerificationDocumentType,
    file: Annotated[UploadFile, File(...)],
    current_user: CurrentUser,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[DevelopmentVerificationUploadData]:
    """Proxy a bounded development file through the production S3 lifecycle."""

    try:
        if not file.filename or not file.filename.strip() or not file.content_type:
            raise GymVerificationDocumentInvalidError(
                "A filename and MIME type are required."
            )
        content = await _read_bounded_file(file)
        service = GymService(
            session=session,
            default_phone_region=settings.default_phone_region,
            storage=S3Storage(settings),
        )
        upload = await service.initiate_verification_upload(
            user_id=current_user.id,
            gym_id=gym_id,
            document_type=document_type,
            payload=GymVerificationUploadRequest(
                filename=file.filename,
                mime_type=file.content_type,
                file_size_bytes=len(content),
            ),
        )
        try:
            timeout = httpx.Timeout(connect=5.0, write=20.0, read=20.0, pool=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.put(
                    upload.upload_url,
                    content=content,
                    headers=upload.required_headers,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            await service.fail_verification_upload(upload.upload_id)
            raise StorageUploadFailedError(
                "The development upload transport failed."
            ) from exc
        document = await service.complete_verification_upload(
            user_id=current_user.id,
            gym_id=gym_id,
            document_type=document_type,
            upload_id=upload.upload_id,
        )
        return APIResponse(
            data=DevelopmentVerificationUploadData(
                upload=await service.get_development_upload_data(upload.upload_id),
                document=document,
            )
        )
    finally:
        await file.close()


async def _read_bounded_file(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_CHUNK_SIZE_BYTES):
        total += len(chunk)
        if total > MAX_GYM_VERIFICATION_FILE_SIZE_BYTES:
            raise GymVerificationDocumentInvalidError(
                "The document exceeds the 10 MB limit."
            )
        chunks.append(chunk)
    if total == 0:
        raise GymVerificationDocumentInvalidError("The document cannot be empty.")
    return b"".join(chunks)
