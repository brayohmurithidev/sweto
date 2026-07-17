class AuthenticationError(Exception):
    """Base exception for authentication-domain failures."""


class InvalidPhoneNumberError(AuthenticationError):
    """Raised when a phone number cannot be parsed or validated."""


class OTPResendCooldownError(AuthenticationError):
    """Raised when another OTP is requested too soon."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Request another code in {retry_after_seconds} seconds.")


class OTPChallengeNotFoundError(AuthenticationError):
    """Raised when an OTP challenge does not exist."""


class OTPChallengeExpiredError(AuthenticationError):
    """Raised when an OTP challenge has expired."""


class OTPChallengeConsumedError(AuthenticationError):
    """Raised when an OTP challenge is no longer pending."""


class InvalidOTPError(AuthenticationError):
    """Raised when a submitted OTP is incorrect."""

    def __init__(self, attempts_remaining: int) -> None:
        self.attempts_remaining = attempts_remaining
        super().__init__("The verification code is incorrect.")


class OTPAttemptsExceededError(AuthenticationError):
    """Raised when the maximum OTP attempts have been reached."""


class UserAccessDeniedError(AuthenticationError):
    """Raised when an account is suspended or deactivated."""


class InvalidAccessTokenError(AuthenticationError):
    """Raised when an access token cannot be validated."""


class AccessTokenExpiredError(AuthenticationError):
    """Raised when an access token has expired."""


class InvalidRefreshTokenError(AuthenticationError):
    """Raised when a refresh token is unknown or invalid."""


class RefreshSessionExpiredError(AuthenticationError):
    """Raised when a refresh session has expired."""


class RefreshSessionRevokedError(AuthenticationError):
    """Raised when a refresh session has already been revoked."""


class SessionNotFoundError(AuthenticationError):
    """Raised when a requested login session does not exist."""


class CurrentSessionRevocationError(AuthenticationError):
    """Raised when attempting to revoke the current session incorrectly."""


class AuthenticationRateLimitError(AuthenticationError):
    """Raised when an authentication rate limit is exceeded."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        retry_after_seconds: int,
        limit: int,
    ) -> None:
        self.code = code
        self.retry_after_seconds = retry_after_seconds
        self.limit = limit

        super().__init__(message)
