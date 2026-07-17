from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.integrations.sms.base import SMSProvider
from app.integrations.sms.dependencies import get_sms_provider
from app.modules.auth.dependencies import (
    CurrentAuthContext,
    CurrentUser,
)
from app.modules.auth.schemas import (
    AuthenticatedUserData,
    LogoutAllData,
    LogoutAllRequest,
    LogoutRequest,
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

ConfiguredSMSProvider = Annotated[
    SMSProvider,
    Depends(get_sms_provider),
]

ConfiguredRateLimiter = Annotated[
    RateLimiter,
    Depends(get_rate_limiter),
]


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
    sms_provider: ConfiguredSMSProvider,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[RequestOTPData]:
    """Send a login OTP to a normalized phone number."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        sms_provider=sms_provider,
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
    sms_provider: ConfiguredSMSProvider,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[VerifyOTPData]:
    """Verify a login OTP and issue authentication tokens."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        sms_provider=sms_provider,
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
    current_user: CurrentUser,
) -> APIResponse[AuthenticatedUserData]:
    """Return the currently authenticated SWETO user."""

    return APIResponse(
        data=AuthenticatedUserData(
            id=current_user.id,
            phone_number=current_user.phone_number,
            status=current_user.status.value,
            is_phone_verified=current_user.is_phone_verified,
        )
    )


@router.post(
    "/refresh",
    response_model=APIResponse[RefreshTokenData],
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    request: Request,
    session: DatabaseSession,
    settings: ApplicationSettings,
    sms_provider: ConfiguredSMSProvider,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[RefreshTokenData]:
    """Rotate a refresh token and issue a new token pair."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        sms_provider=sms_provider,
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
    sms_provider: ConfiguredSMSProvider,
    rate_limiter: ConfiguredRateLimiter,
) -> Response:
    """Revoke the supplied refresh session."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        sms_provider=sms_provider,
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
    sms_provider: ConfiguredSMSProvider,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[SessionListData]:
    """List active login sessions for the current user."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        sms_provider=sms_provider,
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
    sms_provider: ConfiguredSMSProvider,
    rate_limiter: ConfiguredRateLimiter,
) -> Response:
    """Revoke another active login session."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        sms_provider=sms_provider,
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
    sms_provider: ConfiguredSMSProvider,
    rate_limiter: ConfiguredRateLimiter,
) -> APIResponse[LogoutAllData]:
    """Revoke all login sessions for the current user."""

    service = AuthenticationService(
        session=session,
        settings=settings,
        sms_provider=sms_provider,
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
