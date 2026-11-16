"""Numbers for the gym owner's Home tab, by the gym's own calendar."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gyms.permissions import GymPermission, role_can
from app.modules.members.enums import (
    CheckInResult,
    GymMemberStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.members.models import GymCheckIn, GymMember, GymMembership, Payment
from app.modules.members.periods import EXPIRING_WITHIN_DAYS, add_months
from app.modules.members.repository import current_start_column, paid_until_column
from app.modules.members.schemas import (
    ActivityItem,
    DailyRevenue,
    DashboardData,
    RevenueSummary,
)
from app.modules.members.service import GymMemberService
from app.modules.profiles.models import UserProfile

RECENT_ITEMS = 8


def _local_midnight(day: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=zone)


class DashboardService:
    def __init__(self, *, session: AsyncSession, members: GymMemberService) -> None:
        self.session = session
        self.members = members

    async def summary(self, *, user_id: UUID, gym_id: UUID) -> DashboardData:
        gym = await self.members._gym_for(
            user_id=user_id, gym_id=gym_id, permission=GymPermission.VIEW_MEMBERS
        )
        zone = ZoneInfo(gym.timezone)
        today = self.members._today(gym)
        month_start = today.replace(day=1)
        last_month_start = add_months(month_start, -1)

        paid_until = paid_until_column()
        current = select(func.count()).where(
            GymMember.gym_id == gym.id,
            GymMember.status == GymMemberStatus.ACTIVE,
            # Paid but starting on a later day: not active yet.
            current_start_column(today) <= today,
        )
        active = await self.session.scalar(current.where(paid_until >= today)) or 0
        expiring = (
            await self.session.scalar(
                current.where(
                    paid_until.between(
                        today, today + timedelta(days=EXPIRING_WITHIN_DAYS - 1)
                    )
                )
            )
            or 0
        )

        day_start = _local_midnight(today, zone)
        check_ins = (
            await self.session.scalar(
                select(func.count()).where(
                    GymCheckIn.gym_id == gym.id,
                    GymCheckIn.result == CheckInResult.ALLOWED,
                    GymCheckIn.repeat_visit.is_(False),
                    GymCheckIn.checked_in_at >= day_start,
                    GymCheckIn.checked_in_at < day_start + timedelta(days=1),
                )
            )
            or 0
        )

        # Revenue is only for roles that may see the gym's finances.
        staff = await self.members.staff.get_user_membership(
            user_id=user_id, gym_id=gym.id
        )
        revenue = (
            await self._revenue(gym.id, zone, today, month_start, last_month_start)
            if staff is not None and role_can(staff.role, GymPermission.VIEW_FINANCE)
            else None
        )
        first_name = await self._first_name(user_id)
        return DashboardData(
            gym_name=gym.name,
            owner_first_name=first_name,
            today=today,
            active_members=active,
            expiring_members=expiring,
            check_ins_today=check_ins,
            revenue=revenue,
            recent_activity=await self._activity(gym.id),
        )

    async def _revenue(
        self,
        gym_id: UUID,
        zone: ZoneInfo,
        today: date,
        month_start: date,
        last_month_start: date,
    ) -> RevenueSummary:
        local_day = cast(func.timezone(str(zone), Payment.paid_at), Date)
        rows = (
            await self.session.execute(
                select(local_day, func.sum(Payment.amount))
                .where(
                    Payment.gym_id == gym_id,
                    Payment.status == PaymentStatus.COMPLETED,
                    Payment.paid_at >= _local_midnight(last_month_start, zone),
                    Payment.paid_at < _local_midnight(today + timedelta(days=1), zone),
                )
                .group_by(local_day)
            )
        ).all()
        by_day: dict[date, Decimal] = {day: amount for day, amount in rows}
        this_month = sum((v for d, v in by_day.items() if d >= month_start), Decimal(0))
        last_month = sum((v for d, v in by_day.items() if d < month_start), Decimal(0))
        change = (
            None
            if last_month == 0
            else round(float((this_month - last_month) / last_month * 100), 1)
        )
        daily = [
            DailyRevenue(
                date=month_start + timedelta(days=offset),
                amount=by_day.get(month_start + timedelta(days=offset), Decimal(0)),
            )
            for offset in range((today - month_start).days + 1)
        ]
        return RevenueSummary(
            currency="KES",
            this_month=this_month,
            last_month=last_month,
            change_percent=change,
            daily=daily,
        )

    async def _activity(self, gym_id: UUID) -> list[ActivityItem]:
        check_ins = (
            await self.session.execute(
                select(GymCheckIn, GymMember.full_name)
                .outerjoin(GymMember, GymMember.id == GymCheckIn.member_id)
                .where(GymCheckIn.gym_id == gym_id)
                .order_by(GymCheckIn.checked_in_at.desc())
                .limit(RECENT_ITEMS)
            )
        ).all()
        payments = (
            await self.session.execute(
                select(Payment, GymMembership, GymMember.full_name)
                .join(GymMembership, GymMembership.id == Payment.membership_id)
                .join(GymMember, GymMember.id == GymMembership.member_id)
                .where(
                    Payment.gym_id == gym_id,
                    Payment.status == PaymentStatus.COMPLETED,
                )
                .order_by(Payment.paid_at.desc())
                .limit(RECENT_ITEMS)
            )
        ).all()
        added = (
            await self.session.execute(
                select(GymMember)
                .where(
                    GymMember.gym_id == gym_id,
                    # An archived member (e.g. added by mistake) isn't news.
                    GymMember.status == GymMemberStatus.ACTIVE,
                )
                .order_by(GymMember.created_at.desc())
                .limit(RECENT_ITEMS)
            )
        ).scalars()

        items = [
            ActivityItem(
                kind="check_in",
                at=check_in.checked_in_at,
                member_id=check_in.member_id,
                member_name=name,
                detail="Checked in"
                if check_in.result == CheckInResult.ALLOWED
                else f"Refused: {check_in.result.value.replace('_', ' ')}",
                ok=check_in.result == CheckInResult.ALLOWED,
            )
            for check_in, name in check_ins
        ]
        items += [
            ActivityItem(
                kind="payment",
                at=payment.paid_at or payment.created_at,
                member_id=membership.member_id,
                member_name=name,
                detail=f"Paid {payment.currency} {payment.amount:,.0f} "
                f"({'M-Pesa' if payment.method == PaymentMethod.MPESA else 'cash'}), "
                f"{membership.plan_name}",
                ok=True,
            )
            for payment, membership, name in payments
        ]
        items += [
            ActivityItem(
                kind="member_added",
                at=member.created_at,
                member_id=member.id,
                member_name=member.full_name,
                detail="New member",
                ok=True,
            )
            for member in added
        ]
        items.sort(key=lambda item: item.at, reverse=True)
        return items[:RECENT_ITEMS]

    async def _first_name(self, user_id: UUID) -> str | None:
        full_name = await self.session.scalar(
            select(UserProfile.full_name).where(UserProfile.user_id == user_id)
        )
        if not full_name or not full_name.strip():
            return None
        return full_name.split()[0]
