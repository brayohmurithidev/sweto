from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import CurrentUser
from app.modules.members.dashboard_service import DashboardService
from app.modules.members.router import MemberService
from app.modules.members.schemas import DashboardData
from app.shared.responses import APIResponse

router = APIRouter(prefix="/gyms/{gym_id}", tags=["Gym dashboard"])


def get_dashboard_service(members: MemberService) -> DashboardService:
    return DashboardService(session=members.session, members=members)


@router.get("/dashboard", response_model=APIResponse[DashboardData])
async def get_dashboard(
    gym_id: UUID,
    current_user: CurrentUser,
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> APIResponse[DashboardData]:
    """Home tab numbers: members, today's check-ins, revenue and activity."""

    data = await service.summary(user_id=current_user.id, gym_id=gym_id)
    return APIResponse(data=data)
