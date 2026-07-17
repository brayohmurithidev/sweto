from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(StrEnum):
    """Possible user account states"""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class OTPPurpose(StrEnum):
    """Operations that require OTP verification"""

    LOGIN = "login"
    PHONE_VERIFICATION = "phone_verification"
    ACCOUNT_RECOVERY = "account_recovery"
    PHONE_CHANGE = "phone_change"


class OTPStatus(StrEnum):
    """Lifecycle status of an OTP challenge"""

    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class SessionStatus(StrEnum):
    """Lifecycle status of an authenticated session."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AuthEventType(StrEnum):
    """Security and authentication events recorded by SWETO."""

    OTP_REQUESTED = "otp_requested"
    OTP_REQUEST_BLOCKED = "otp_request_blocked"
    OTP_VERIFIED = "otp_verified"
    OTP_VERIFICATION_FAILED = "otp_verification_failed"
    OTP_EXPIRED = "otp_expired"
    OTP_ATTEMPTS_EXCEEDED = "otp_attempts_exceeded"

    LOGIN_SUCCEEDED = "login_succeeded"
    LOGIN_DENIED = "login_denied"
    PASSWORD_CHANGED = "password_changed"

    TOKEN_REFRESHED = "token_refreshed"
    TOKEN_REFRESH_FAILED = "token_refresh_failed"

    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"

    SESSION_REVOKED = "session_revoked"
    SESSION_EXPIRED = "session_expired"


class AuthEventOutcome(StrEnum):
    """Outcome of an authentication event."""

    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
