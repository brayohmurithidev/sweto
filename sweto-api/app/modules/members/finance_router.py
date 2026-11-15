from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.modules.auth.dependencies import CurrentUser
from app.modules.members.enums import PaymentMethod, PaymentStatus
from app.modules.members.finance_service import FinanceService
from app.modules.members.router import MemberService
from app.modules.members.schemas import (
    FinanceSummaryData,
    FinanceTransactionListData,
)
from app.shared.responses import APIResponse

router = APIRouter(prefix="/gyms/{gym_id}/finance", tags=["Gym finance"])

MonthQuery = Annotated[
    str | None,
    Query(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="YYYY-MM by the gym's calendar; this month when left out.",
    ),
]


def get_finance_service(members: MemberService) -> FinanceService:
    return FinanceService(session=members.session, members=members)


def _month(value: str | None) -> date | None:
    if value is None:
        return None
    year, month = value.split("-")
    return date(int(year), int(month), 1)


@router.get("", response_model=APIResponse[FinanceSummaryData])
async def get_finance_summary(
    gym_id: UUID,
    current_user: CurrentUser,
    service: Annotated[FinanceService, Depends(get_finance_service)],
    month: MonthQuery = None,
) -> APIResponse[FinanceSummaryData]:
    """A month's revenue: totals, cash vs M-Pesa, by plan, and a 6-month trend."""

    data = await service.summary(
        user_id=current_user.id, gym_id=gym_id, month=_month(month)
    )
    return APIResponse(data=data)


@router.get("/transactions", response_model=APIResponse[FinanceTransactionListData])
async def list_finance_transactions(
    gym_id: UUID,
    current_user: CurrentUser,
    service: Annotated[FinanceService, Depends(get_finance_service)],
    month: MonthQuery = None,
    method: PaymentMethod | None = None,
    payment_status: Annotated[PaymentStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> APIResponse[FinanceTransactionListData]:
    """A month's payments, newest first, including failed and waiting M-Pesa."""

    data = await service.transactions(
        user_id=current_user.id,
        gym_id=gym_id,
        month=_month(month),
        method=method,
        status=payment_status,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)
