from unittest.mock import Mock
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.core.config import Settings
from app.modules.gyms.enums import GymVerificationDocumentType
from app.storage.exceptions import (
    StorageAccessDeniedError,
    StorageNotConfiguredError,
    StorageObjectNotFoundError,
    StorageServiceUnavailableError,
)
from app.storage.keys import ALLOWED_EXTENSION_BY_MIME_TYPE, build_gym_verification_key
from app.storage.s3 import S3Storage


def storage_settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"aws_s3_uploads_bucket": "private-uploads"})


def test_verification_key_is_server_controlled_and_uses_mime_extension() -> None:
    gym_id = uuid4()
    upload_id = uuid4()
    key = build_gym_verification_key(
        gym_id=gym_id,
        document_type=GymVerificationDocumentType.BUSINESS_REGISTRATION,
        upload_id=upload_id,
        mime_type="application/pdf",
    )

    assert key == (f"gyms/{gym_id}/verification/business_registration/{upload_id}.pdf")
    assert ".." not in key
    assert not key.startswith("/")
    assert "original-name" not in key
    assert ALLOWED_EXTENSION_BY_MIME_TYPE["image/jpeg"] == ".jpg"


def test_storage_requires_bucket(settings: Settings) -> None:
    with pytest.raises(StorageNotConfiguredError):
        S3Storage(settings.model_copy(update={"aws_s3_uploads_bucket": None}))


@pytest.mark.parametrize(
    ("access_key", "secret_key"),
    [("access-key-only", None), (None, "secret-key-only")],
)
def test_aws_credentials_must_be_a_pair(
    settings: Settings, access_key: str | None, secret_key: str | None
) -> None:
    values = settings.model_dump()
    values["aws_access_key_id"] = access_key
    values["aws_secret_access_key"] = secret_key

    with pytest.raises(ValueError, match="must be configured together"):
        Settings.model_validate(values)


def test_storage_uses_default_credential_chain_without_credentials(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = Mock()
    boto_client = Mock(return_value=client)
    monkeypatch.setattr("app.storage.s3.boto3.client", boto_client)
    configured = settings.model_copy(
        update={
            "aws_s3_uploads_bucket": "private-uploads",
            "aws_s3_endpoint_url": "",
            "aws_access_key_id": None,
            "aws_secret_access_key": None,
        }
    )

    S3Storage(configured)

    assert boto_client.call_args.kwargs == {"region_name": configured.aws_region}


def test_storage_uses_configured_credential_pair(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = Mock()
    boto_client = Mock(return_value=client)
    monkeypatch.setattr("app.storage.s3.boto3.client", boto_client)
    configured = settings.model_copy(
        update={
            "aws_s3_uploads_bucket": "private-uploads",
            "aws_s3_endpoint_url": "http://localhost:4566",
            "aws_access_key_id": "access-key",
            "aws_secret_access_key": "secret-key",
        }
    )

    storage = S3Storage(configured)

    assert storage._client is client
    assert boto_client.call_args.kwargs == {
        "region_name": configured.aws_region,
        "endpoint_url": "http://localhost:4566",
        "aws_access_key_id": "access-key",
        "aws_secret_access_key": "secret-key",
    }


@pytest.mark.asyncio
async def test_presigned_upload_binds_key_and_content_type(settings: Settings) -> None:
    storage = S3Storage(storage_settings(settings))
    storage._client = Mock()
    storage._client.generate_presigned_url.return_value = (
        "https://signed.example/upload"
    )

    result = await storage.create_upload_url(
        key="gyms/gym/verification/other/upload.pdf", mime_type="application/pdf"
    )

    assert result.url == "https://signed.example/upload"
    assert storage._client.generate_presigned_url.call_args.kwargs["Params"] == {
        "Bucket": "private-uploads",
        "Key": "gyms/gym/verification/other/upload.pdf",
        "ContentType": "application/pdf",
    }


@pytest.mark.asyncio
async def test_head_object_and_aws_errors_are_safely_mapped(settings: Settings) -> None:
    storage = S3Storage(storage_settings(settings))
    storage._client = Mock()
    storage._client.head_object.return_value = {
        "ContentType": "Application/PDF ",
        "ContentLength": 7,
        "ETag": '"etag-value"',
    }
    metadata = await storage.head_object(key="gyms/key.pdf")
    assert (metadata.content_type, metadata.content_length, metadata.etag) == (
        "application/pdf",
        7,
        "etag-value",
    )

    storage._client.head_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}, "ResponseMetadata": {"HTTPStatusCode": 404}},
        "HeadObject",
    )
    with pytest.raises(StorageObjectNotFoundError):
        await storage.head_object(key="missing")

    storage._client.head_object.side_effect = ClientError(
        {
            "Error": {"Code": "AccessDenied"},
            "ResponseMetadata": {"HTTPStatusCode": 403},
        },
        "HeadObject",
    )
    with pytest.raises(StorageAccessDeniedError):
        await storage.head_object(key="denied")

    storage._client.head_object.side_effect = EndpointConnectionError(
        endpoint_url="https://s3"
    )
    with pytest.raises(StorageServiceUnavailableError):
        await storage.head_object(key="offline")
