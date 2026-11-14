from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.integrations.sms.base import SMSProvider
from app.integrations.sms.dependencies import get_sms_provider
from app.modules.auth.dependencies import CurrentUser
from app.modules.members.enums import GymMemberStatus, MemberStanding
from app.modules.members.notifier import MemberNotifier
from app.modules.members.schemas import (
    CreateGymMemberRequest,
    GymMemberData,
    GymMemberDetailData,
    GymMemberListData,
    RecordCashPaymentData,
    RecordCashPaymentRequest,
    SetMemberSmsRequest,
    UpdateGymMemberRequest,
)
from app.modules.members.service import GymMemberService
from app.shared.clock import Clock, get_clock
from app.shared.responses import APIResponse

router = APIRouter(prefix="/gyms/{gym_id}/members", tags=["Gym Members"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentClock = Annotated[Clock, Depends(get_clock)]


def get_member_service(
    session: DatabaseSession,
    clock: CurrentClock,
    settings: Annotated[Settings, Depends(get_settings)],
    sms: Annotated[SMSProvider, Depends(get_sms_provider)],
) -> GymMemberService:
    return GymMemberService(
        session=session,
        clock=clock,
        notifier=MemberNotifier(
            session=session,
            sms=sms,
            clock=clock,
            timeout_seconds=settings.sms_send_timeout_seconds,
        ),
        code_secret=settings.otp_hash_secret,
    )


MemberService = Annotated[GymMemberService, Depends(get_member_service)]


@router.get("", response_model=APIResponse[GymMemberListData])
async def list_gym_members(
    gym_id: UUID,
    current_user: CurrentUser,
    service: MemberService,
    search: Annotated[str | None, Query(max_length=100)] = None,
    standing: Annotated[
        MemberStanding | None,
        Query(
            description=(
                "active: paid through today or later (includes expiring); "
                "expiring: ends within 7 days, today included; expired; "
                "no_membership."
            )
        ),
    ] = None,
    member_status: Annotated[GymMemberStatus, Query(alias="status")] = (
        GymMemberStatus.ACTIVE
    ),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> APIResponse[GymMemberListData]:
    """List members, searchable by name or phone and filterable by standing."""

    data = await service.list_members(
        user_id=current_user.id,
        gym_id=gym_id,
        status=member_status,
        search=search,
        standing=standing,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.post(
    "",
    response_model=APIResponse[GymMemberData],
    status_code=status.HTTP_201_CREATED,
)
async def create_gym_member(
    gym_id: UUID,
    payload: CreateGymMemberRequest,
    current_user: CurrentUser,
    service: MemberService,
) -> APIResponse[GymMemberData]:
    """Add an existing member by name and phone number."""

    data = await service.create_member(
        user_id=current_user.id, gym_id=gym_id, payload=payload
    )
    return APIResponse(data=data)


@router.get("/{member_id}", response_model=APIResponse[GymMemberDetailData])
async def get_gym_member(
    gym_id: UUID,
    member_id: UUID,
    current_user: CurrentUser,
    service: MemberService,
) -> APIResponse[GymMemberDetailData]:
    """Return a member with their membership and payment history."""

    data = await service.get_member(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id
    )
    return APIResponse(data=data)


@router.patch("/{member_id}", response_model=APIResponse[GymMemberData])
async def update_gym_member(
    gym_id: UUID,
    member_id: UUID,
    payload: UpdateGymMemberRequest,
    current_user: CurrentUser,
    service: MemberService,
) -> APIResponse[GymMemberData]:
    """Change a member's name or phone number."""

    data = await service.update_member(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id, payload=payload
    )
    return APIResponse(data=data)


@router.post("/{member_id}/archive", response_model=APIResponse[GymMemberData])
async def archive_gym_member(
    gym_id: UUID,
    member_id: UUID,
    current_user: CurrentUser,
    service: MemberService,
) -> APIResponse[GymMemberData]:
    """Archive a member. Their history is kept; they can be restored."""

    data = await service.set_archived(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id, archived=True
    )
    return APIResponse(data=data)


@router.post("/{member_id}/restore", response_model=APIResponse[GymMemberData])
async def restore_gym_member(
    gym_id: UUID,
    member_id: UUID,
    current_user: CurrentUser,
    service: MemberService,
) -> APIResponse[GymMemberData]:
    """Bring an archived member back to the active list."""

    data = await service.set_archived(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id, archived=False
    )
    return APIResponse(data=data)


@router.post(
    "/{member_id}/payments/cash",
    response_model=APIResponse[RecordCashPaymentData],
    status_code=status.HTTP_201_CREATED,
)
async def record_cash_payment(
    gym_id: UUID,
    member_id: UUID,
    payload: RecordCashPaymentRequest,
    current_user: CurrentUser,
    service: MemberService,
) -> APIResponse[RecordCashPaymentData]:
    """Record a cash payment; it adds the membership period it pays for."""

    data = await service.record_cash_payment(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id, payload=payload
    )
    return APIResponse(data=data)


@router.put("/{member_id}/sms", response_model=APIResponse[GymMemberData])
async def set_gym_member_sms(
    gym_id: UUID,
    member_id: UUID,
    payload: SetMemberSmsRequest,
    current_user: CurrentUser,
    service: MemberService,
) -> APIResponse[GymMemberData]:
    """Record the member's SMS consent (staff confirm it) or their opt-out."""

    data = await service.set_sms(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id, payload=payload
    )
    return APIResponse(data=data)
