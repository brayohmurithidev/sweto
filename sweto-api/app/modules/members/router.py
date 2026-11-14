from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.members.enums import GymMemberStatus, MemberStanding
from app.modules.members.schemas import (
    CreateGymMemberRequest,
    GymMemberData,
    GymMemberDetailData,
    GymMemberListData,
    RecordCashPaymentData,
    RecordCashPaymentRequest,
    UpdateGymMemberRequest,
)
from app.modules.members.service import GymMemberService
from app.shared.clock import Clock, get_clock
from app.shared.responses import APIResponse

router = APIRouter(prefix="/gyms/{gym_id}/members", tags=["Gym Members"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CurrentClock = Annotated[Clock, Depends(get_clock)]


def _service(session: AsyncSession, clock: Clock) -> GymMemberService:
    return GymMemberService(session=session, clock=clock)


@router.get("", response_model=APIResponse[GymMemberListData])
async def list_gym_members(
    gym_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    clock: CurrentClock,
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

    data = await _service(session, clock).list_members(
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
    session: DatabaseSession,
    clock: CurrentClock,
) -> APIResponse[GymMemberData]:
    """Add an existing member by name and phone number."""

    data = await _service(session, clock).create_member(
        user_id=current_user.id, gym_id=gym_id, payload=payload
    )
    return APIResponse(data=data)


@router.get("/{member_id}", response_model=APIResponse[GymMemberDetailData])
async def get_gym_member(
    gym_id: UUID,
    member_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    clock: CurrentClock,
) -> APIResponse[GymMemberDetailData]:
    """Return a member with their membership and payment history."""

    data = await _service(session, clock).get_member(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id
    )
    return APIResponse(data=data)


@router.patch("/{member_id}", response_model=APIResponse[GymMemberData])
async def update_gym_member(
    gym_id: UUID,
    member_id: UUID,
    payload: UpdateGymMemberRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    clock: CurrentClock,
) -> APIResponse[GymMemberData]:
    """Change a member's name or phone number."""

    data = await _service(session, clock).update_member(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id, payload=payload
    )
    return APIResponse(data=data)


@router.post("/{member_id}/archive", response_model=APIResponse[GymMemberData])
async def archive_gym_member(
    gym_id: UUID,
    member_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    clock: CurrentClock,
) -> APIResponse[GymMemberData]:
    """Archive a member. Their history is kept; they can be restored."""

    data = await _service(session, clock).set_archived(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id, archived=True
    )
    return APIResponse(data=data)


@router.post("/{member_id}/restore", response_model=APIResponse[GymMemberData])
async def restore_gym_member(
    gym_id: UUID,
    member_id: UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
    clock: CurrentClock,
) -> APIResponse[GymMemberData]:
    """Bring an archived member back to the active list."""

    data = await _service(session, clock).set_archived(
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
    session: DatabaseSession,
    clock: CurrentClock,
) -> APIResponse[RecordCashPaymentData]:
    """Record a cash payment; it adds the membership period it pays for."""

    data = await _service(session, clock).record_cash_payment(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id, payload=payload
    )
    return APIResponse(data=data)
