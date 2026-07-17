import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import Settings
from app.modules.auth.exceptions import (
    AccessTokenExpiredError,
    InvalidAccessTokenError,
)


def create_access_token(
    *,
    user_id: UUID,
    session_id: UUID,
    settings: Settings,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    """Create a signed short-lived JWT access token."""

    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expiry_minutes)

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "access",
        "iat": issued_at,
        "exp": expires_at,
        "jti": str(uuid4()),
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return token, expires_at


def generate_refresh_token() -> str:
    """Generate a cryptographically secure opaque refresh token."""

    return secrets.token_urlsafe(64)


def hash_refresh_token(refresh_token: str) -> str:
    """Hash a refresh token before database storage."""

    return hashlib.sha256(refresh_token.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Validated claims extracted from an access token."""

    user_id: UUID
    session_id: UUID
    token_id: UUID


def decode_access_token(
    *,
    token: str,
    settings: Settings,
) -> AccessTokenClaims:
    """Validate and decode a SWETO access token."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={
                "require": [
                    "sub",
                    "sid",
                    "jti",
                    "type",
                    "iat",
                    "exp",
                ],
            },
        )
    except ExpiredSignatureError as exc:
        raise AccessTokenExpiredError("The access token has expired.") from exc
    except InvalidTokenError as exc:
        raise InvalidAccessTokenError("The access token is invalid.") from exc

    if payload.get("type") != "access":
        raise InvalidAccessTokenError("The token is not an access token.")

    try:
        return AccessTokenClaims(
            user_id=UUID(payload["sub"]),
            session_id=UUID(payload["sid"]),
            token_id=UUID(payload["jti"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessTokenError(
            "The access token contains invalid claims."
        ) from exc
