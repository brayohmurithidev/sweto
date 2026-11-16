"""Money for the gym owner's Finance tab, by the gym's own calendar.

Revenue counts completed payments on the local day they were paid. Pending
and failed M-Pesa prompts are counted apart and never add to revenue.
"""

import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.gyms.permissions import GymPermission
from app.modules.members.enums import (
    PaymentMethod,
    PaymentStatus,
    PaymentTransactionStatus,
)
from app.modules.members.exceptions import InvalidFinanceMonthError
from app.modules.members.models import (
    GymMember,
    GymMembership,
    Payment,
    PaymentTransaction,
)
from app.modules.members.periods import add_months
from app.modules.members.schemas import (
    FinanceSummaryData,
    FinanceTransactionData,
    FinanceTransactionListData,
    MethodTotal,
    MonthTotal,
    PlanTotal,
)
from app.modules.members.service import GymMemberService
from app.modules.profiles.models import UserProfile

CURRENCY = "KES"
TREND_MONTHS = 6


def _local_midnight(day: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=zone)


def _month_end(month_start: date) -> date:
    last = calendar.monthrange(month_start.year, month_start.month)[1]
    return month_start.replace(day=last)


def _payment_at() -> ColumnElement[datetime]:
    """When it was paid, or when it was asked for if it never was."""

    return func.coalesce(Payment.paid_at, Payment.created_at)


class FinanceService:
    def __init__(self, *, session: AsyncSession, members: GymMemberService) -> None:
        self.session = session
        self.members = members

    async def summary(
        self, *, user_id: UUID, gym_id: UUID, month: date | None
    ) -> FinanceSummaryData:
        gym = await self.members._gym_for(
            user_id=user_id, gym_id=gym_id, permission=GymPermission.VIEW_FINANCE
        )
        zone = ZoneInfo(gym.timezone)
        today = self.members._today(gym)
        month_start, through = self._span(month, today)
        is_current = month_start == today.replace(day=1)

        completed = self._completed(gym.id, zone, month_start, through)
        total, count = (
            await self.session.execute(
                select(func.coalesce(func.sum(Payment.amount), 0), func.count()).where(
                    *completed
                )
            )
        ).one()

        by_method_rows = dict(
            (method, (amount, n))
            for method, amount, n in (
                await self.session.execute(
                    select(Payment.method, func.sum(Payment.amount), func.count())
                    .where(*completed)
                    .group_by(Payment.method)
                )
            ).all()
        )
        by_method = [
            MethodTotal(
                method=method,
                amount=by_method_rows.get(method, (Decimal(0), 0))[0],
                count=by_method_rows.get(method, (Decimal(0), 0))[1],
            )
            for method in (PaymentMethod.CASH, PaymentMethod.MPESA)
        ]

        by_plan = [
            PlanTotal(plan_name=name, amount=amount, count=n)
            for name, amount, n in (
                await self.session.execute(
                    select(
                        GymMembership.plan_name,
                        func.sum(Payment.amount),
                        func.count(),
                    )
                    .join(GymMembership, GymMembership.id == Payment.membership_id)
                    .where(*completed)
                    .group_by(GymMembership.plan_name)
                    .order_by(func.sum(Payment.amount).desc(), GymMembership.plan_name)
                )
            ).all()
        ]

        # A month in progress is compared with the same days of the month
        # before; a finished month with the whole month before.
        previous_start = add_months(month_start, -1)
        previous_through = (
            add_months(through, -1) if is_current else month_start - timedelta(days=1)
        )
        previous_total = await self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                *self._completed(gym.id, zone, previous_start, previous_through)
            )
        ) or Decimal(0)
        change = (
            None
            if previous_total == 0
            else round(float((total - previous_total) / previous_total * 100), 1)
        )

        failed, pending = await self._mpesa_attempts(gym.id, zone, month_start, through)

        return FinanceSummaryData(
            currency=CURRENCY,
            month=month_start,
            through=through,
            is_current_month=is_current,
            total=total,
            payments_count=count,
            previous_month_total=previous_total,
            change_percent=change,
            by_method=by_method,
            by_plan=by_plan,
            trend=await self._trend(gym.id, zone, month_start, through),
            failed_mpesa_count=failed,
            pending_mpesa_count=pending,
        )

    async def transactions(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        month: date | None,
        method: PaymentMethod | None,
        status: PaymentStatus | None,
        limit: int,
        offset: int,
    ) -> FinanceTransactionListData:
        gym = await self.members._gym_for(
            user_id=user_id, gym_id=gym_id, permission=GymPermission.VIEW_FINANCE
        )
        zone = ZoneInfo(gym.timezone)
        month_start, through = self._span(month, self.members._today(gym))

        at = _payment_at()
        filters: list[ColumnElement[bool]] = [
            Payment.gym_id == gym.id,
            at >= _local_midnight(month_start, zone),
            at < _local_midnight(through + timedelta(days=1), zone),
        ]
        if method is not None:
            filters.append(Payment.method == method)
        if status is not None:
            filters.append(Payment.status == status)

        total = await self.session.scalar(
            select(func.count()).select_from(Payment).where(*filters)
        )

        receipt = (
            select(PaymentTransaction.provider_receipt)
            .where(
                PaymentTransaction.payment_id == Payment.id,
                PaymentTransaction.status == PaymentTransactionStatus.SUCCEEDED,
            )
            .order_by(PaymentTransaction.completed_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(
                    Payment,
                    at,
                    GymMembership.plan_name,
                    GymMember.id,
                    GymMember.full_name,
                    receipt,
                    UserProfile.full_name,
                )
                .join(GymMembership, GymMembership.id == Payment.membership_id)
                .join(GymMember, GymMember.id == GymMembership.member_id)
                .outerjoin(
                    UserProfile, UserProfile.user_id == Payment.recorded_by_user_id
                )
                .where(*filters)
                .order_by(at.desc(), Payment.id.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()

        return FinanceTransactionListData(
            transactions=[
                FinanceTransactionData(
                    payment_id=payment.id,
                    member_id=member_id,
                    member_name=member_name,
                    plan_name=plan_name,
                    amount=payment.amount,
                    currency=payment.currency,
                    method=payment.method,
                    status=payment.status,
                    at=paid_at,
                    receipt=receipt_number,
                    recorded_by_name=recorder or None,
                )
                for (
                    payment,
                    paid_at,
                    plan_name,
                    member_id,
                    member_name,
                    receipt_number,
                    recorder,
                ) in rows
            ],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def _span(month: date | None, today: date) -> tuple[date, date]:
        """First day of the month asked for and the last day to count."""

        current = today.replace(day=1)
        month_start = current if month is None else month.replace(day=1)
        if month_start > current:
            raise InvalidFinanceMonthError("That month hasn't started yet.")
        through = today if month_start == current else _month_end(month_start)
        return month_start, through

    @staticmethod
    def _completed(
        gym_id: UUID, zone: ZoneInfo, first: date, last: date
    ) -> list[ColumnElement[bool]]:
        """Completed payments paid between two local days, both included."""

        return [
            Payment.gym_id == gym_id,
            Payment.status == PaymentStatus.COMPLETED,
            Payment.paid_at >= _local_midnight(first, zone),
            Payment.paid_at < _local_midnight(last + timedelta(days=1), zone),
        ]

    async def _trend(
        self, gym_id: UUID, zone: ZoneInfo, month_start: date, through: date
    ) -> list[MonthTotal]:
        first = add_months(month_start, -(TREND_MONTHS - 1))
        local_month = cast(
            func.date_trunc("month", func.timezone(str(zone), Payment.paid_at)), Date
        )
        rows = (
            await self.session.execute(
                select(local_month, func.sum(Payment.amount))
                .where(*self._completed(gym_id, zone, first, through))
                .group_by(local_month)
            )
        ).all()
        by_month: dict[date, Decimal] = {month: amount for month, amount in rows}
        return [
            MonthTotal(
                month=add_months(first, offset),
                amount=by_month.get(add_months(first, offset), Decimal(0)),
            )
            for offset in range(TREND_MONTHS)
        ]

    async def _mpesa_attempts(
        self, gym_id: UUID, zone: ZoneInfo, month_start: date, through: date
    ) -> tuple[int, int]:
        result = (
            await self.session.execute(
                select(Payment.status, func.count())
                .where(
                    Payment.gym_id == gym_id,
                    Payment.method == PaymentMethod.MPESA,
                    Payment.status.in_([PaymentStatus.FAILED, PaymentStatus.PENDING]),
                    Payment.created_at >= _local_midnight(month_start, zone),
                    Payment.created_at
                    < _local_midnight(through + timedelta(days=1), zone),
                )
                .group_by(Payment.status)
            )
        ).all()
        counts: dict[PaymentStatus, int] = {status: n for status, n in result}
        return (
            counts.get(PaymentStatus.FAILED, 0),
            counts.get(PaymentStatus.PENDING, 0),
        )
