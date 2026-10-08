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


class OTPDeliveryChannel(StrEnum):
    """How a one-time password reaches the user."""

    SMS = "sms"
    WHATSAPP = "whatsapp"


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
    OTP_DELIVERY_FAILED = "otp_delivery_failed"
    OTP_VERIFIED = "otp_verified"
    OTP_VERIFICATION_FAILED = "otp_verification_failed"
    OTP_EXPIRED = "otp_expired"
    OTP_ATTEMPTS_EXCEEDED = "otp_attempts_exceeded"

    LOGIN_SUCCEEDED = "login_succeeded"
    LOGIN_DENIED = "login_denied"
    PASSWORD_CHANGED = "password_changed"
    SUPER_ADMIN_BOOTSTRAPPED = "super_admin_bootstrapped"
    ADMIN_CREATED = "admin_created"
    ADMIN_STATUS_CHANGED = "admin_status_changed"
    ADMIN_ROLE_CHANGED = "admin_role_changed"
    ADMIN_OPERATION_BLOCKED = "admin_operation_blocked"
    GYM_VERIFICATION_DOCUMENT_REGISTERED = "gym_verification_document_registered"
    GYM_VERIFICATION_SUBMITTED = "gym_verification_submitted"
    GYM_VERIFICATION_APPROVED = "gym_verification_approved"
    GYM_VERIFICATION_REJECTED = "gym_verification_rejected"
    STORAGE_UPLOAD_INITIATED = "storage_upload_initiated"
    STORAGE_UPLOAD_COMPLETED = "storage_upload_completed"
    STORAGE_UPLOAD_FAILED = "storage_upload_failed"
    VERIFICATION_DOCUMENT_DOWNLOAD_REQUESTED = (
        "verification_document_download_requested"
    )

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
