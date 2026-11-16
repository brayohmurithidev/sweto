"""Downloads for the gym's own records (CSV)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.modules.auth.dependencies import CurrentUser
from app.modules.members.exports import GymExports
from app.modules.members.finance_router import MonthQuery, _month, get_finance_service
from app.modules.members.finance_service import FinanceService
from app.modules.members.router import MemberService

router = APIRouter(prefix="/gyms/{gym_id}/exports", tags=["Gym exports"])


def get_exports(
    members: MemberService,
    finance: Annotated[FinanceService, Depends(get_finance_service)],
) -> GymExports:
    return GymExports(members=members, finance=finance)


Exports = Annotated[GymExports, Depends(get_exports)]


def _download(name: str, body: str) -> Response:
    return Response(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get(
    "/payments.csv",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_payments(
    gym_id: UUID, current_user: CurrentUser, exports: Exports, month: MonthQuery = None
) -> Response:
    """A month's payments as CSV. Owner and manager."""

    name, body = await exports.payments_csv(
        user_id=current_user.id, gym_id=gym_id, month=_month(month)
    )
    return _download(name, body)


@router.get(
    "/members.csv",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_members(
    gym_id: UUID, current_user: CurrentUser, exports: Exports
) -> Response:
    """Every member, with phone numbers, as CSV. Owner and manager."""

    name, body = await exports.members_csv(user_id=current_user.id, gym_id=gym_id)
    return _download(name, body)
