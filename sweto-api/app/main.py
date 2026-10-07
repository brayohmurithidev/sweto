from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    access_token_expired_handler,
    admin_error_handler,
    amenity_not_found_handler,
    authentication_rate_limit_handler,
    current_password_incorrect_handler,
    current_session_revocation_handler,
    gym_access_denied_handler,
    gym_already_exists_handler,
    gym_not_found_handler,
    gym_slug_conflict_handler,
    gym_verification_error_handler,
    invalid_access_token_handler,
    invalid_email_or_password_handler,
    invalid_otp_handler,
    invalid_phone_number_handler,
    invalid_profile_update_handler,
    invalid_refresh_token_handler,
    otp_attempts_exceeded_handler,
    otp_challenge_consumed_handler,
    otp_challenge_expired_handler,
    otp_challenge_not_found_handler,
    otp_delivery_failed_handler,
    otp_resend_cooldown_handler,
    password_change_required_handler,
    password_login_not_available_handler,
    password_policy_violation_handler,
    password_reuse_not_allowed_handler,
    refresh_session_expired_handler,
    refresh_session_revoked_handler,
    session_not_found_handler,
    storage_error_handler,
    user_access_denied_handler,
)
from app.core.redis import close_redis
from app.database.session import engine
from app.modules.admin.exceptions import (
    AdminEmailAlreadyExistsError,
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
from app.storage.exceptions import StorageError

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """
    Manage application startup and shutdown.

    Future startup tasks may include:
    - Verifying database connectivity
    - initializng monitoring
    - connecting to Redis

    Future shutdown tasks may include:
    - closing database connections/pools
    - closing Redis connections

    """
    yield

    await close_redis()
    await engine.dispose()


def create_application() -> FastAPI:
    """
    Application factory used by development, testing and production
    """
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    application.include_router(api_router)
    for admin_exception in (
        AdminEmailAlreadyExistsError,
        AdminNotFoundError,
        PlatformRoleRequiredError,
        ProtectedSystemUserError,
        SelfAdministrationNotAllowedError,
        InvalidAdminStatusError,
        InvalidAdminRoleChangeError,
        SuperAdminIntegrityError,
        SuperAdminConfigurationError,
    ):
        application.add_exception_handler(admin_exception, admin_error_handler)
    application.add_exception_handler(
        InvalidPhoneNumberError,
        invalid_phone_number_handler,
    )

    application.add_exception_handler(
        OTPResendCooldownError,
        otp_resend_cooldown_handler,
    )

    application.add_exception_handler(
        OTPDeliveryFailedError,
        otp_delivery_failed_handler,
    )

    application.add_exception_handler(
        OTPChallengeNotFoundError,
        otp_challenge_not_found_handler,
    )

    application.add_exception_handler(
        OTPChallengeExpiredError,
        otp_challenge_expired_handler,
    )

    application.add_exception_handler(
        OTPChallengeConsumedError,
        otp_challenge_consumed_handler,
    )

    application.add_exception_handler(
        InvalidOTPError,
        invalid_otp_handler,
    )

    application.add_exception_handler(
        OTPAttemptsExceededError,
        otp_attempts_exceeded_handler,
    )

    application.add_exception_handler(
        UserAccessDeniedError,
        user_access_denied_handler,
    )
    application.add_exception_handler(
        InvalidEmailOrPasswordError,
        invalid_email_or_password_handler,
    )
    application.add_exception_handler(
        PasswordChangeRequiredError,
        password_change_required_handler,
    )
    application.add_exception_handler(
        CurrentPasswordIncorrectError,
        current_password_incorrect_handler,
    )
    application.add_exception_handler(
        PasswordReuseNotAllowedError,
        password_reuse_not_allowed_handler,
    )
    application.add_exception_handler(
        PasswordPolicyViolationError,
        password_policy_violation_handler,
    )
    application.add_exception_handler(
        PasswordLoginNotAvailableError,
        password_login_not_available_handler,
    )

    application.add_exception_handler(
        InvalidAccessTokenError,
        invalid_access_token_handler,
    )

    application.add_exception_handler(
        AccessTokenExpiredError,
        access_token_expired_handler,
    )

    application.add_exception_handler(
        InvalidRefreshTokenError,
        invalid_refresh_token_handler,
    )

    application.add_exception_handler(
        RefreshSessionExpiredError,
        refresh_session_expired_handler,
    )

    application.add_exception_handler(
        RefreshSessionRevokedError,
        refresh_session_revoked_handler,
    )

    application.add_exception_handler(
        SessionNotFoundError,
        session_not_found_handler,
    )

    application.add_exception_handler(
        CurrentSessionRevocationError,
        current_session_revocation_handler,
    )

    application.add_exception_handler(
        AuthenticationRateLimitError,
        authentication_rate_limit_handler,
    )

    application.add_exception_handler(
        InvalidProfileUpdateError,
        invalid_profile_update_handler,
    )
    application.add_exception_handler(
        GymNotFoundError,
        gym_not_found_handler,
    )

    application.add_exception_handler(
        GymAccessDeniedError,
        gym_access_denied_handler,
    )
    for verification_exception in (
        GymVerificationDocumentNotFoundError,
        GymVerificationDocumentInvalidError,
        GymVerificationRequirementsError,
        GymProfileIncompleteError,
        GymVerificationAlreadyPendingError,
        GymVerificationAlreadyApprovedError,
        GymVerificationReviewInProgressError,
        GymVerificationNotPendingError,
        GymVerificationRejectionReasonRequiredError,
        GymVerificationAccessDeniedError,
    ):
        application.add_exception_handler(
            verification_exception, gym_verification_error_handler
        )

    application.add_exception_handler(
        GymAlreadyExistsError,
        gym_already_exists_handler,
    )

    application.add_exception_handler(
        GymSlugConflictError,
        gym_slug_conflict_handler,
    )
    application.add_exception_handler(StorageError, storage_error_handler)

    application.add_exception_handler(
        AmenityNotFoundError,
        amenity_not_found_handler,
    )

    return application


app = create_application()
