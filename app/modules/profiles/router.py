from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.profiles.schemas import (
    AccountSetupData,
    OnboardingStatusData,
    ProfileData,
    SelectAccountRoleRequest,
    UpdateProfileData,
    UpdateProfileRequest,
)
from app.modules.profiles.service import ProfileService
from app.shared.responses import APIResponse

account_router = APIRouter(
    prefix="/account",
    tags=["Account Setup"],
)

profile_router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)


DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


@account_router.post(
    "/roles",
    response_model=APIResponse[AccountSetupData],
)
async def select_account_role(
    payload: SelectAccountRoleRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> APIResponse[AccountSetupData]:
    """Select or enable a SWETO account experience."""

    service = ProfileService(session=session)

    data = await service.select_account_role(
        user_id=current_user.id,
        role=payload.role,
    )

    return APIResponse(data=data)


@account_router.get(
    "/onboarding",
    response_model=APIResponse[OnboardingStatusData],
)
async def get_onboarding_status(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> APIResponse[OnboardingStatusData]:
    """Return the user's current onboarding state."""

    service = ProfileService(session=session)

    data = await service.get_onboarding_status(
        user_id=current_user.id,
    )

    return APIResponse(data=data)


@profile_router.get(
    "",
    response_model=APIResponse[ProfileData],
)
async def get_profile(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> APIResponse[ProfileData]:
    """Return the current user's personal profile."""

    service = ProfileService(session=session)

    data = await service.get_profile(
        user=current_user,
    )

    return APIResponse(data=data)


@profile_router.patch(
    "",
    response_model=APIResponse[UpdateProfileData],
)
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> APIResponse[UpdateProfileData]:
    """Update the current user's personal profile."""

    service = ProfileService(session=session)

    data = await service.update_profile(
        user=current_user,
        payload=payload,
    )

    return APIResponse(data=data)
