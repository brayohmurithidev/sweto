from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.modules.admin.dependencies import require_platform_roles
from app.modules.auth.enums import UserRole
from app.modules.auth.models import User
from app.modules.gyms.enums import GymVerificationStatus
from app.modules.gyms.schemas import (
    GymVerificationData,
    GymVerificationListData,
    GymVerificationReviewRequest,
)
from app.modules.gyms.service import GymService
from app.shared.responses import APIResponse

router = APIRouter(prefix="/admin/gym-verifications", tags=["Gym Verification"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
ApplicationSettings = Annotated[Settings, Depends(get_settings)]
PlatformReviewer = Annotated[
    User,
    Depends(require_platform_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
]


@router.get("", response_model=APIResponse[GymVerificationListData])
async def list_gym_verifications(
    reviewer: PlatformReviewer,
    session: DatabaseSession,
    settings: ApplicationSettings,
    status: GymVerificationStatus = GymVerificationStatus.PENDING,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> APIResponse[GymVerificationListData]:
    service = GymService(
        session=session, default_phone_region=settings.default_phone_region
    )
    return APIResponse(
        data=await service.list_verifications(
            reviewer=reviewer, status=status, limit=limit, offset=offset
        )
    )


@router.get("/{gym_id}", response_model=APIResponse[GymVerificationData])
async def get_gym_verification_for_review(
    gym_id: UUID,
    reviewer: PlatformReviewer,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymVerificationData]:
    service = GymService(
        session=session, default_phone_region=settings.default_phone_region
    )
    return APIResponse(
        data=await service.get_verification(user=reviewer, gym_id=gym_id)
    )


@router.post("/{gym_id}/review", response_model=APIResponse[GymVerificationData])
async def review_gym_verification(
    gym_id: UUID,
    payload: GymVerificationReviewRequest,
    reviewer: PlatformReviewer,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> APIResponse[GymVerificationData]:
    service = GymService(
        session=session, default_phone_region=settings.default_phone_region
    )
    return APIResponse(
        data=await service.review_verification(
            reviewer=reviewer, gym_id=gym_id, payload=payload
        )
    )
