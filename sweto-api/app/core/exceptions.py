from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.modules.admin.exceptions import (
    AdminEmailAlreadyExistsError,
    AdminError,
    AdminNotFoundError,
    InvalidAdminRoleChangeError,
    InvalidAdminStatusError,
    PlatformRoleRequiredError,
    ProtectedSystemUserError,
    SelfAdministrationNotAllowedError,
    SuperAdminConfigurationError,
    SuperAdminIntegrityError,
)
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
    OTPDeliveryFailedError,
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
    GymPhotoLimitReachedError,
    GymPhotoUploadInvalidError,
    GymProfileIncompleteError,
    GymSlugConflictError,
    GymVerificationAccessDeniedError,
    GymVerificationAlreadyApprovedError,
    GymVerificationAlreadyPendingError,
    GymVerificationDocumentInvalidError,
    GymVerificationDocumentNotFoundError,
    GymVerificationNotPendingError,
    GymVerificationRejectionReasonRequiredError,
    GymVerificationRequirementsError,
    GymVerificationReviewInProgressError,
)
from app.modules.profiles.exceptions import (
    InvalidProfileUpdateError,
)
from app.storage.exceptions import (
    StorageAccessDeniedError,
    StorageError,
    StorageNotConfiguredError,
    StorageObjectNotFoundError,
    StorageObjectSizeMismatchError,
    StorageObjectTypeMismatchError,
    StorageServiceUnavailableError,
    StorageUploadAlreadyCompletedError,
    StorageUploadExpiredError,
    StorageUploadFailedError,
    StorageUploadNotFoundError,
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


async def admin_error_handler(_: Request, exception: Exception) -> JSONResponse:
    if not isinstance(exception, AdminError):
        raise exception
    mappings: dict[type[AdminError], tuple[int, str]] = {
        AdminEmailAlreadyExistsError: (409, "ADMIN_EMAIL_ALREADY_EXISTS"),
        AdminNotFoundError: (404, "ADMIN_NOT_FOUND"),
        PlatformRoleRequiredError: (403, "PLATFORM_ROLE_REQUIRED"),
        ProtectedSystemUserError: (403, "PROTECTED_SYSTEM_USER"),
        SelfAdministrationNotAllowedError: (
            403,
            "SELF_ADMINISTRATION_NOT_ALLOWED",
        ),
        InvalidAdminStatusError: (422, "INVALID_ADMIN_STATUS"),
        InvalidAdminRoleChangeError: (422, "INVALID_ADMIN_ROLE_CHANGE"),
        SuperAdminIntegrityError: (409, "SUPER_ADMIN_INTEGRITY_ERROR"),
        SuperAdminConfigurationError: (422, "SUPER_ADMIN_CONFIGURATION_ERROR"),
    }
    status_code, code = mappings.get(type(exception), (400, "ADMIN_ERROR"))
    return error_response(status_code=status_code, code=code, message=str(exception))


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


async def otp_delivery_failed_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    """Return a retryable error when the SMS provider could not send the code."""

    if not isinstance(exception, OTPDeliveryFailedError):
        raise exception

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": False,
            "error": {
                "code": "OTP_DELIVERY_FAILED",
                "message": str(exception),
                "details": {},
            },
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


async def gym_verification_error_handler(
    _: Request, exception: Exception
) -> JSONResponse:
    mappings: dict[type[Exception], tuple[int, str]] = {
        GymVerificationDocumentNotFoundError: (
            404,
            "GYM_VERIFICATION_DOCUMENT_NOT_FOUND",
        ),
        GymVerificationDocumentInvalidError: (422, "GYM_VERIFICATION_DOCUMENT_INVALID"),
        GymVerificationRequirementsError: (422, "GYM_VERIFICATION_DOCUMENTS_MISSING"),
        GymProfileIncompleteError: (422, "GYM_PROFILE_INCOMPLETE"),
        GymVerificationAlreadyPendingError: (409, "GYM_VERIFICATION_ALREADY_PENDING"),
        GymVerificationAlreadyApprovedError: (409, "GYM_VERIFICATION_ALREADY_APPROVED"),
        GymVerificationReviewInProgressError: (
            409,
            "GYM_VERIFICATION_REVIEW_IN_PROGRESS",
        ),
        GymVerificationNotPendingError: (409, "GYM_VERIFICATION_NOT_PENDING"),
        GymVerificationRejectionReasonRequiredError: (
            422,
            "GYM_VERIFICATION_REJECTION_REASON_REQUIRED",
        ),
        GymVerificationAccessDeniedError: (403, "GYM_VERIFICATION_ACCESS_DENIED"),
    }
    matched = mappings.get(type(exception))
    if matched is None:
        raise exception
    status_code, code = matched
    details: dict[str, object] | None = None
    if isinstance(exception, GymVerificationRequirementsError):
        details = {"missing_document_types": exception.missing_document_types}
    elif isinstance(exception, GymProfileIncompleteError):
        details = {"next_step": exception.next_step}
    return error_response(
        status_code=status_code, code=code, message=str(exception), details=details
    )


async def storage_error_handler(_: Request, exception: Exception) -> JSONResponse:
    if not isinstance(exception, StorageError):
        raise exception
    mappings: dict[type[StorageError], tuple[int, str]] = {
        StorageNotConfiguredError: (503, "STORAGE_NOT_CONFIGURED"),
        StorageUploadNotFoundError: (404, "STORAGE_UPLOAD_NOT_FOUND"),
        StorageUploadExpiredError: (409, "STORAGE_UPLOAD_EXPIRED"),
        StorageUploadAlreadyCompletedError: (409, "STORAGE_UPLOAD_ALREADY_COMPLETED"),
        StorageObjectNotFoundError: (404, "STORAGE_OBJECT_NOT_FOUND"),
        StorageObjectSizeMismatchError: (422, "STORAGE_OBJECT_SIZE_MISMATCH"),
        StorageObjectTypeMismatchError: (422, "STORAGE_OBJECT_TYPE_MISMATCH"),
        StorageUploadFailedError: (422, "STORAGE_UPLOAD_FAILED"),
        StorageAccessDeniedError: (403, "STORAGE_ACCESS_DENIED"),
        StorageServiceUnavailableError: (503, "STORAGE_SERVICE_UNAVAILABLE"),
    }
    status_code, code = mappings.get(type(exception), (500, "STORAGE_ERROR"))
    return error_response(status_code=status_code, code=code, message=str(exception))


async def gym_photo_error_handler(_: Request, exception: Exception) -> JSONResponse:
    """Return client errors for rejected gym-photo uploads."""

    if isinstance(exception, GymPhotoLimitReachedError):
        return error_response(
            status_code=status.HTTP_409_CONFLICT,
            code="GYM_PHOTO_LIMIT_REACHED",
            message=str(exception),
        )
    if isinstance(exception, GymPhotoUploadInvalidError):
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="GYM_PHOTO_INVALID",
            message=str(exception),
        )
    raise exception


async def gym_day_pass_not_found_handler(
    _: Request,
    exception: Exception,
) -> JSONResponse:
    """Return a client error when pricing names an unknown day pass."""

    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="DAY_PASS_NOT_FOUND",
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
