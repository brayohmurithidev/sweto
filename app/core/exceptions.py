from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.modules.auth.exceptions import (
    AccessTokenExpiredError,
    AuthenticationRateLimitError,
    CurrentPasswordIncorrectError,
    CurrentSessionRevocationError,
    InvalidAccessTokenError,
    InvalidEmailOrPasswordError,
    InvalidOTPError,
    InvalidPhoneNumberError,
    InvalidRefreshTokenError,
    OTPAttemptsExceededError,
    OTPChallengeConsumedError,
    OTPChallengeExpiredError,
    OTPChallengeNotFoundError,
    OTPResendCooldownError,
    PasswordChangeRequiredError,
    PasswordLoginNotAvailableError,
    PasswordPolicyViolationError,
    PasswordReuseNotAllowedError,
    RefreshSessionExpiredError,
    RefreshSessionRevokedError,
    SessionNotFoundError,
    UserAccessDeniedError,
)
from app.modules.gyms.exceptions import (
    AmenityNotFoundError,
    GymAccessDeniedError,
    GymAlreadyExistsError,
    GymNotFoundError,
    GymSlugConflictError,
)
from app.modules.profiles.exceptions import (
    InvalidProfileUpdateError,
)


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Create a standard API error response."""

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
        },
        headers=headers,
    )


async def invalid_phone_number_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    """Return a validation response for invalid phone numbers."""

    if not isinstance(exception, InvalidPhoneNumberError):
        raise exception

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "error": {
                "code": "INVALID_PHONE_NUMBER",
                "message": str(exception),
                "details": {},
            },
        },
    )


async def otp_resend_cooldown_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    """Return a rate-limit response during the OTP resend cooldown."""

    if not isinstance(exception, OTPResendCooldownError):
        raise exception

    retry_after_seconds = exception.retry_after_seconds

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "error": {
                "code": "OTP_RESEND_COOLDOWN",
                "message": str(exception),
                "details": {
                    "retry_after_seconds": retry_after_seconds,
                },
            },
        },
        headers={
            "Retry-After": str(retry_after_seconds),
        },
    )


async def otp_challenge_not_found_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, OTPChallengeNotFoundError):
        raise exception

    return error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="OTP_CHALLENGE_NOT_FOUND",
        message=str(exception),
    )


async def otp_challenge_expired_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, OTPChallengeExpiredError):
        raise exception

    return error_response(
        status_code=status.HTTP_410_GONE,
        code="OTP_EXPIRED",
        message=str(exception),
    )


async def otp_challenge_consumed_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, OTPChallengeConsumedError):
        raise exception

    return error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="OTP_ALREADY_USED",
        message=str(exception),
    )


async def invalid_otp_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, InvalidOTPError):
        raise exception

    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="INVALID_OTP",
        message=str(exception),
        details={
            "attempts_remaining": exception.attempts_remaining,
        },
    )


async def otp_attempts_exceeded_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, OTPAttemptsExceededError):
        raise exception

    return error_response(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code="OTP_ATTEMPTS_EXCEEDED",
        message=str(exception),
    )


async def user_access_denied_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, UserAccessDeniedError):
        raise exception

    return error_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="USER_ACCESS_DENIED",
        message=str(exception),
    )


async def invalid_email_or_password_handler(
    _: Request, exception: Exception
) -> JSONResponse:
    if not isinstance(exception, InvalidEmailOrPasswordError):
        raise exception
    return error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="INVALID_EMAIL_OR_PASSWORD",
        message=str(exception),
    )


async def password_change_required_handler(
    _: Request, exception: Exception
) -> JSONResponse:
    if not isinstance(exception, PasswordChangeRequiredError):
        raise exception
    return error_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="PASSWORD_CHANGE_REQUIRED",
        message=str(exception),
    )


async def current_password_incorrect_handler(
    _: Request, exception: Exception
) -> JSONResponse:
    if not isinstance(exception, CurrentPasswordIncorrectError):
        raise exception
    return error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="CURRENT_PASSWORD_INCORRECT",
        message=str(exception),
    )


async def password_reuse_not_allowed_handler(
    _: Request, exception: Exception
) -> JSONResponse:
    if not isinstance(exception, PasswordReuseNotAllowedError):
        raise exception
    return error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="PASSWORD_REUSE_NOT_ALLOWED",
        message=str(exception),
    )


async def password_policy_violation_handler(
    _: Request, exception: Exception
) -> JSONResponse:
    if not isinstance(exception, PasswordPolicyViolationError):
        raise exception
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="PASSWORD_POLICY_VIOLATION",
        message=str(exception),
    )


async def password_login_not_available_handler(
    _: Request, exception: Exception
) -> JSONResponse:
    if not isinstance(exception, PasswordLoginNotAvailableError):
        raise exception
    return error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="PASSWORD_LOGIN_NOT_AVAILABLE",
        message=str(exception),
    )


async def invalid_access_token_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, InvalidAccessTokenError):
        raise exception

    return error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="INVALID_ACCESS_TOKEN",
        message=str(exception),
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


async def access_token_expired_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, AccessTokenExpiredError):
        raise exception

    return error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="ACCESS_TOKEN_EXPIRED",
        message=str(exception),
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


async def invalid_refresh_token_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, InvalidRefreshTokenError):
        raise exception

    return error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="INVALID_REFRESH_TOKEN",
        message=str(exception),
    )


async def refresh_session_expired_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, RefreshSessionExpiredError):
        raise exception

    return error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="REFRESH_SESSION_EXPIRED",
        message=str(exception),
    )


async def refresh_session_revoked_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, RefreshSessionRevokedError):
        raise exception

    return error_response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="REFRESH_SESSION_REVOKED",
        message=str(exception),
    )


async def session_not_found_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, SessionNotFoundError):
        raise exception

    return error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="SESSION_NOT_FOUND",
        message=str(exception),
    )


async def current_session_revocation_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(
        exception,
        CurrentSessionRevocationError,
    ):
        raise exception

    return error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="CURRENT_SESSION_REVOCATION_NOT_ALLOWED",
        message=str(exception),
    )


async def authentication_rate_limit_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(
        exception,
        AuthenticationRateLimitError,
    ):
        raise exception

    return error_response(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code=exception.code,
        message=str(exception),
        details={
            "limit": exception.limit,
            "retry_after_seconds": (exception.retry_after_seconds),
        },
        headers={
            "Retry-After": str(exception.retry_after_seconds),
        },
    )


async def invalid_profile_update_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(
        exception,
        InvalidProfileUpdateError,
    ):
        raise exception

    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="INVALID_PROFILE_UPDATE",
        message=str(exception),
    )


async def gym_not_found_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, GymNotFoundError):
        raise exception

    return error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="GYM_NOT_FOUND",
        message=str(exception),
    )


async def gym_access_denied_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, GymAccessDeniedError):
        raise exception

    return error_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="GYM_ACCESS_DENIED",
        message=str(exception),
    )


async def gym_already_exists_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, GymAlreadyExistsError):
        raise exception

    return error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="GYM_ALREADY_EXISTS",
        message=str(exception),
    )


async def gym_slug_conflict_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, GymSlugConflictError):
        raise exception

    return error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="GYM_SLUG_CONFLICT",
        message=str(exception),
    )


async def amenity_not_found_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, AmenityNotFoundError):
        raise exception

    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="INVALID_AMENITIES",
        message=str(exception),
    )
