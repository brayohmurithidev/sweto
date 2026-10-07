from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    content_type: str
    content_length: int
    etag: str | None
