"""Gym staff: the signed-in person's own access, and the owner's staff list."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.integrations.sms.base import SMSProvider
from app.integrations.sms.dependencies import get_sms_provider
from app.modules.auth.dependencies import CurrentUser
from app.modules.gyms.schemas import (
    AddGymStaffData,
    AddGymStaffRequest,
    GymStaffAccessData,
    GymStaffData,
    GymStaffListData,
    UpdateGymStaffRequest,
)
from app.modules.gyms.staff_service import GymStaffService
from app.shared.clock import Clock, get_clock
from app.shared.responses import APIResponse

router = APIRouter(prefix="/gyms/{gym_id}/staff", tags=["Gym Staff"])


def get_staff_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    settings: Annotated[Settings, Depends(get_settings)],
    sms: Annotated[SMSProvider, Depends(get_sms_provider)],
) -> GymStaffService:
    return GymStaffService(
        session=session,
        sms=sms,
        clock=clock,
        sms_timeout_seconds=settings.sms_send_timeout_seconds,
    )


StaffService = Annotated[GymStaffService, Depends(get_staff_service)]


@router.get("/me", response_model=APIResponse[GymStaffAccessData])
async def get_my_gym_access(
    gym_id: UUID, current_user: CurrentUser, service: StaffService
) -> APIResponse[GymStaffAccessData]:
    """Your role at this gym and what it lets you do."""

    return APIResponse(
        data=await service.my_access(user_id=current_user.id, gym_id=gym_id)
    )


@router.get("", response_model=APIResponse[GymStaffListData])
async def list_gym_staff(
    gym_id: UUID, current_user: CurrentUser, service: StaffService
) -> APIResponse[GymStaffListData]:
    """Everyone who works at the gym. Owner only."""

    return APIResponse(
        data=await service.list_staff(user_id=current_user.id, gym_id=gym_id)
    )


@router.post(
    "",
    response_model=APIResponse[AddGymStaffData],
    status_code=status.HTTP_201_CREATED,
)
async def add_gym_staff(
    gym_id: UUID,
    payload: AddGymStaffRequest,
    current_user: CurrentUser,
    service: StaffService,
) -> APIResponse[AddGymStaffData]:
    """Add someone by phone number and text them an invite. Owner only."""

    return APIResponse(
        data=await service.add_staff(
            user_id=current_user.id, gym_id=gym_id, payload=payload
        )
    )


@router.patch("/{staff_id}", response_model=APIResponse[GymStaffData])
async def update_gym_staff(
    gym_id: UUID,
    staff_id: UUID,
    payload: UpdateGymStaffRequest,
    current_user: CurrentUser,
    service: StaffService,
) -> APIResponse[GymStaffData]:
    """Change someone's role, or suspend / reinstate them. Owner only."""

    return APIResponse(
        data=await service.update_staff(
            user_id=current_user.id,
            gym_id=gym_id,
            staff_id=staff_id,
            payload=payload,
        )
    )


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_gym_staff(
    gym_id: UUID, staff_id: UUID, current_user: CurrentUser, service: StaffService
) -> None:
    """Remove someone. They are signed out and lose access at once. Owner only."""

    await service.remove_staff(
        user_id=current_user.id, gym_id=gym_id, staff_id=staff_id
    )
