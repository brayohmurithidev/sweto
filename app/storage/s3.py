from datetime import UTC, datetime, timedelta
from typing import Any, cast

import anyio
import boto3  # type: ignore[import-untyped]
from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
)

from app.core.config import Settings
from app.storage.exceptions import (
    StorageAccessDeniedError,
    StorageNotConfiguredError,
    StorageObjectNotFoundError,
    StorageServiceUnavailableError,
    StorageUploadFailedError,
)
from app.storage.schemas import ObjectMetadata, PresignedUpload


class S3Storage:
    """Small async facade around Boto3's synchronous S3 client."""

    def __init__(self, settings: Settings) -> None:
        if not settings.aws_s3_uploads_bucket:
            raise StorageNotConfiguredError("Private S3 uploads are not configured.")
        self.bucket = settings.aws_s3_uploads_bucket
        self.upload_expiry_seconds = settings.aws_s3_presigned_upload_expiry_seconds
        self.download_expiry_seconds = settings.aws_s3_presigned_download_expiry_seconds
        self._client: Any = boto3.client(
            "s3",
            region_name=settings.aws_region,
            endpoint_url=settings.aws_s3_endpoint_url,
        )

    async def create_upload_url(self, *, key: str, mime_type: str) -> PresignedUpload:
        def generate() -> str:
            return cast(
                str,
                self._client.generate_presigned_url(
                    ClientMethod="put_object",
                    Params={
                        "Bucket": self.bucket,
                        "Key": key,
                        "ContentType": mime_type,
                    },
                    ExpiresIn=self.upload_expiry_seconds,
                    HttpMethod="PUT",
                ),
            )

        return PresignedUpload(
            url=await self._run(generate),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=self.upload_expiry_seconds),
        )

    async def create_download_url(self, *, key: str) -> PresignedUpload:
        def generate() -> str:
            return cast(
                str,
                self._client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=self.download_expiry_seconds,
                ),
            )

        return PresignedUpload(
            url=await self._run(generate),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=self.download_expiry_seconds),
        )

    async def head_object(self, *, key: str) -> ObjectMetadata:
        def head() -> ObjectMetadata:
            response = self._client.head_object(Bucket=self.bucket, Key=key)
            return ObjectMetadata(
                content_type=str(response.get("ContentType", "")).strip().lower(),
                content_length=int(response["ContentLength"]),
                etag=str(response["ETag"]).strip('"') if response.get("ETag") else None,
            )

        return cast(ObjectMetadata, await self._run(head))

    async def delete_object(self, *, key: str) -> None:
        await self._run(lambda: self._client.delete_object(Bucket=self.bucket, Key=key))

    async def _run(self, operation: Any) -> Any:
        try:
            return await anyio.to_thread.run_sync(operation)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            status = int(
                exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
            )
            if code in {"NoSuchKey", "NotFound", "404"} or status == 404:
                raise StorageObjectNotFoundError(
                    "The uploaded object was not found."
                ) from exc
            if code in {"AccessDenied", "403"} or status == 403:
                raise StorageAccessDeniedError("Storage access was denied.") from exc
            raise StorageUploadFailedError("The storage operation failed.") from exc
        except (EndpointConnectionError, BotoCoreError) as exc:
            raise StorageServiceUnavailableError(
                "Storage is temporarily unavailable."
            ) from exc
