from typing import Annotated
from uuid import UUID

import phonenumbers
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.modules.auth.dependencies import (
    BaseAuthContext,
    BaseCurrentUser,
    CurrentAuthContext,
)
from app.modules.auth.otp_delivery import OTPDelivery, get_otp_delivery
from app.modules.auth.schemas import (
    AuthenticatedUserData,
    ChangePasswordData,
    ChangePasswordRequest,
    LogoutAllData,
    LogoutAllRequest,
    LogoutRequest,
    OTPDeliveryData,
    PasswordLoginData,
    PasswordLoginRequest,
    PhoneCountriesData,
    PhoneCountryData,
    RefreshTokenData,
    RefreshTokenRequest,
    RequestOTPData,
    RequestOTPRequest,
    SessionListData,
    VerifyOTPData,
    VerifyOTPRequest,
)
from app.modules.auth.service import AuthenticationService
from app.rate_limit.base import RateLimiter
from app.rate_limit.dependencies import get_rate_limiter
from app.shared.responses import APIResponse

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]

ApplicationSettings = Annotated[
    Settings,
    Depends(get_settings),
]

ConfiguredOTPDelivery = Annotated[
    OTPDelivery,
    Depends(get_otp_delivery),
]

ConfiguredRateLimiter = Annotated[
    RateLimiter,
    Depends(get_rate_limiter),
]


@router.post(
    "/password/login",
    response_model=APIResponse[PasswordLoginData],
)
async def password_login(
    payload: PasswordLoginRequest,
    request: Request,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[PasswordLoginData]:
    """Authenticate an email/password account using standard sessions."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )
    data = await service.password_login(
        payload=payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return APIResponse(data=data)


@router.get(
    "/phone-countries",
    response_model=APIResponse[PhoneCountriesData],
)
async def phone_countries(
    otp_delivery: ConfiguredOTPDelivery,
) -> APIResponse[PhoneCountriesData]:
    """Countries whose numbers can sign in now, with their code channel."""

    return APIResponse(
        data=PhoneCountriesData(
            countries=[
                PhoneCountryData(
                    region=region,
                    dial_code=str(phonenumbers.country_code_for_region(region)),
                    delivery_channel=channel,
                )
                for region, channel in otp_delivery.available_regions()
            ]
        )
    )


@router.get(
    "/otp-challenges/{challenge_id}/delivery",
    response_model=APIResponse[OTPDeliveryData],
)
async def otp_delivery_status(
    challenge_id: UUID,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[OTPDeliveryData]:
    """Where a sign-in code is on its way (accepted, delivered, failed...)."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )
    return APIResponse(data=await service.get_otp_delivery(challenge_id=challenge_id))


@router.post(
    "/request-otp",
    response_model=APIResponse[RequestOTPData],
    status_code=status.HTTP_201_CREATED,
)
async def request_otp(
    payload: RequestOTPRequest,
    request: Request,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[RequestOTPData]:
    """Send a login OTP to a normalized phone number."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )

    data = await service.request_login_otp(
        raw_phone_number=payload.phone_number,
        requested_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return APIResponse(data=data)


@router.post(
    "/verify-otp",
    response_model=APIResponse[VerifyOTPData],
)
async def verify_otp(
    payload: VerifyOTPRequest,
    request: Request,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[VerifyOTPData]:
    """Verify a login OTP and issue authentication tokens."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )

    data = await service.verify_login_otp(
        payload=payload,
        ip_address=(request.client.host if request.client is not None else None),
        user_agent=request.headers.get("user-agent"),
    )

    return APIResponse(data=data)


@router.get(
    "/me",
    response_model=APIResponse[AuthenticatedUserData],
)
async def get_me(
    current_user: BaseCurrentUser,
) -> APIResponse[AuthenticatedUserData]:
    """Return the currently authenticated SWETO user."""

    return APIResponse(
        data=AuthenticatedUserData(
            id=current_user.id,
            phone_number=current_user.phone_number,
            email=current_user.email,
            status=current_user.status.value,
            is_phone_verified=current_user.is_phone_verified,
            role=current_user.role,
            must_change_password=current_user.must_change_password,
        )
    )


@router.post(
    "/change-password",
    response_model=APIResponse[ChangePasswordData],
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    auth_context: BaseAuthContext,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[ChangePasswordData]:
    """Replace the current password and invalidate all login sessions."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )
    data = await service.change_password(
        user_id=auth_context.user.id,
        payload=payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return APIResponse(data=data)


@router.post(
    "/refresh",
    response_model=APIResponse[RefreshTokenData],
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    request: Request,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[RefreshTokenData]:
    """Rotate a refresh token and issue a new token pair."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )

    data = await service.refresh_tokens(
        payload=payload,
        ip_address=(request.client.host if request.client is not None else None),
        user_agent=request.headers.get("user-agent"),
    )

    return APIResponse(data=data)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def logout(
    payload: LogoutRequest,
    request: Request,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> Response:
    """Revoke the supplied refresh session."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )

    await service.logout(
        refresh_token=payload.refresh_token,
        ip_address=(request.client.host if request.client is not None else None),
        user_agent=request.headers.get("user-agent"),
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/sessions",
    response_model=APIResponse[SessionListData],
)
async def list_sessions(
    auth_context: CurrentAuthContext,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[SessionListData]:
    """List active login sessions for the current user."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )

    data = await service.list_sessions(
        user_id=auth_context.user.id,
        current_session_id=auth_context.session.id,
    )

    return APIResponse(data=data)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def revoke_session(
    session_id: UUID,
    request: Request,
    auth_context: CurrentAuthContext,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> Response:
    """Revoke another active login session."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )

    await service.revoke_session(
        user_id=auth_context.user.id,
        current_session_id=auth_context.session.id,
        target_session_id=session_id,
        ip_address=(request.client.host if request.client is not None else None),
        user_agent=request.headers.get("user-agent"),
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/logout-all",
    response_model=APIResponse[LogoutAllData],
)
async def logout_all(
    payload: LogoutAllRequest,
    request: Request,
    auth_context: CurrentAuthContext,
    session: DatabaseSession,
    settings: ApplicationSettings,
    otp_delivery: ConfiguredOTPDelivery,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[LogoutAllData]:
    """Revoke all login sessions for the current user."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        otp_delivery=otp_delivery,
        rate_limiter=rate_limiter,
    )

    data = await service.logout_all(
        user_id=auth_context.user.id,
        current_session_id=auth_context.session.id,
        keep_current_session=payload.keep_current_session,
        ip_address=(request.client.host if request.client is not None else None),
        user_agent=request.headers.get("user-agent"),
    )

    return APIResponse(data=data)
