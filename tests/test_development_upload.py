from io import BytesIO

import pytest
from fastapi import FastAPI, UploadFile
from starlette.datastructures import Headers

from app.modules.gyms.constants import MAX_GYM_VERIFICATION_FILE_SIZE_BYTES
from app.modules.gyms.dev_router import _read_bounded_file, router
from app.modules.gyms.exceptions import GymVerificationDocumentInvalidError


def upload_file(
    *, filename: str, content: bytes, content_type: str = "application/pdf"
) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_development_upload_openapi_uses_multipart_file_field() -> None:
    application = FastAPI()
    application.include_router(router, prefix="/api/v1")
    operation = application.openapi()["paths"][
        "/api/v1/dev/gyms/{gym_id}/verification/documents/{document_type}/upload"
    ]["post"]
    content = operation["requestBody"]["content"]

    assert "multipart/form-data" in content
    schema = application.openapi()["components"]["schemas"]
    body_reference = content["multipart/form-data"]["schema"]["$ref"].rsplit("/", 1)[-1]
    assert "file" in schema[body_reference]["properties"]


@pytest.mark.asyncio
async def test_development_upload_reader_is_bounded_and_rejects_empty_file() -> None:
    assert (
        await _read_bounded_file(upload_file(filename="valid.pdf", content=b"pdf"))
        == b"pdf"
    )

    with pytest.raises(GymVerificationDocumentInvalidError):
        await _read_bounded_file(upload_file(filename="empty.pdf", content=b""))

    oversized = upload_file(
        filename="large.pdf", content=b"x" * (MAX_GYM_VERIFICATION_FILE_SIZE_BYTES + 1)
    )
    with pytest.raises(GymVerificationDocumentInvalidError):
        await _read_bounded_file(oversized)
