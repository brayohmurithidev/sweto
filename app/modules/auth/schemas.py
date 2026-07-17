from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RequestOTPRequest(BaseModel):
    """Request body for starting OTP authentication."""

    phone_number: str = Field(
        min_length=7,
        max_length=30,
        examples=["+254712345678"],
    )


class RequestOTPData(BaseModel):
    """Response data returned after creating an OTP challenge."""

    challenge_id: UUID
    phone_number: str
    expires_at: datetime
    resend_available_at: datetime
    expires_in_seconds: int


class VerifyOTPRequest(BaseModel):
    """Request body for verifying an OTP challenge."""

    challenge_id: UUID
    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        examples=["123456"],
    )

    device_id: str | None = Field(
        default=None,
        max_length=255,
    )

    device_name: str | None = Field(
        default=None,
        max_length=120,
    )

    platform: str | None = Field(
        default=None,
        max_length=50,
        examples=["ios", "android"],
    )


class AuthenticatedUserData(BaseModel):
    """Authenticated user information."""

    id: UUID
    phone_number: str
    status: str
    is_phone_verified: bool


class TokenData(BaseModel):
    """Issued authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class VerifyOTPData(BaseModel):
    """Response returned after successful OTP verification."""

    user: AuthenticatedUserData
    tokens: TokenData
    is_new_user: bool
    requires_account_setup: bool


class RefreshTokenRequest(BaseModel):
    """Request body for rotating a refresh token."""

    refresh_token: str = Field(
        min_length=40,
        max_length=500,
    )

    device_id: str | None = Field(
        default=None,
        max_length=255,
    )

    device_name: str | None = Field(
        default=None,
        max_length=120,
    )

    platform: str | None = Field(
        default=None,
        max_length=50,
    )


class RefreshTokenData(BaseModel):
    """Tokens returned after refresh-token rotation."""

    tokens: TokenData


class LogoutRequest(BaseModel):
    """Request body for revoking a refresh session."""

    refresh_token: str = Field(
        min_length=40,
        max_length=500,
    )


class SessionData(BaseModel):
    """An authenticated device session."""

    id: UUID
    device_name: str | None
    device_id: str | None
    platform: str | None
    ip_address: str | None
    status: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    is_current: bool


class SessionListData(BaseModel):
    """Active sessions belonging to the authenticated user."""

    sessions: list[SessionData]
    total: int


class LogoutAllRequest(BaseModel):
    """Options for revoking a user's sessions."""

    keep_current_session: bool = True


class LogoutAllData(BaseModel):
    """Result returned after revoking multiple sessions."""

    revoked_sessions: int
    current_session_kept: bool
