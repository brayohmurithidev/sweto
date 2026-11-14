from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.integrations.sms.base import SMSProvider
from app.integrations.sms.dependencies import get_sms_provider
from app.modules.auth.dependencies import CurrentUser
from app.modules.members.check_in_service import CheckInService
from app.modules.members.notifier import MemberNotifier
from app.modules.members.schemas import (
    CheckInCodeData,
    CheckInData,
    CheckInDayData,
    CheckInRequest,
)
from app.rate_limit.base import RateLimiter
from app.rate_limit.dependencies import get_rate_limiter
from app.shared.clock import Clock, get_clock
from app.shared.responses import APIResponse

router = APIRouter(prefix="/gyms/{gym_id}", tags=["Check-in"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentClock = Annotated[Clock, Depends(get_clock)]
ApplicationSettings = Annotated[Settings, Depends(get_settings)]
Limiter = Annotated[RateLimiter, Depends(get_rate_limiter)]


def _service(
    session: AsyncSession,
    clock: Clock,
    settings: Settings,
    limiter: RateLimiter,
    sms: SMSProvider | None = None,
) -> CheckInService:
    notifier = (
        None
        if sms is None
        else MemberNotifier(
            session=session,
            sms=sms,
            clock=clock,
            timeout_seconds=settings.sms_send_timeout_seconds,
        )
    )
    return CheckInService(
        session=session,
        clock=clock,
        settings=settings,
        rate_limiter=limiter,
        notifier=notifier,
    )


@router.post(
    "/members/{member_id}/check-in-code",
    response_model=APIResponse[CheckInCodeData],
    status_code=status.HTTP_201_CREATED,
)
async def issue_check_in_code(
    gym_id: UUID,
    member_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    clock: CurrentClock,
    settings: ApplicationSettings,
    limiter: Limiter,
    sms: Annotated[SMSProvider, Depends(get_sms_provider)],
) -> APIResponse[CheckInCodeData]:
    """Issue a new check-in code, returned once and texted to the member if
    they agreed to SMS. The old code stops working."""

    data = await _service(session, clock, settings, limiter, sms).issue_code(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id
    )
    return APIResponse(data=data)


@router.post("/check-ins", response_model=APIResponse[CheckInData])
async def check_in(
    gym_id: UUID,
    payload: CheckInRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    clock: CurrentClock,
    settings: ApplicationSettings,
    limiter: Limiter,
) -> APIResponse[CheckInData]:
    """Check a member in by code. Refusals are answered (and logged) too."""

    data = await _service(session, clock, settings, limiter).check_in(
        user_id=current_user.id, gym_id=gym_id, raw_code=payload.code
    )
    return APIResponse(data=data)


@router.get("/check-ins", response_model=APIResponse[CheckInDayData])
async def list_check_ins(
    gym_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    clock: CurrentClock,
    settings: ApplicationSettings,
    limiter: Limiter,
    day: Annotated[
        date | None,
        Query(alias="date", description="Gym-local date; defaults to today."),
    ] = None,
) -> APIResponse[CheckInDayData]:
    """A day's check-ins, newest first, with the visit count for the dashboard."""

    data = await _service(session, clock, settings, limiter).day(
        user_id=current_user.id, gym_id=gym_id, day=day
    )
    return APIResponse(data=data)
