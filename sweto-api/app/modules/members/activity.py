"""What happened at the gym and who did it: check-ins, payments and new
members, newest first. Home shows the latest few; the activity list pages
through all of it and can follow one staff member."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.members.enums import (
    CheckInResult,
    GymMemberStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.members.models import GymCheckIn, GymMember, GymMembership, Payment
from app.modules.members.schemas import ActivityItem
from app.modules.profiles.models import UserProfile


def _name(full_name: str | None) -> str | None:
    return full_name.strip() if full_name and full_name.strip() else None


async def gym_activity(
    session: AsyncSession,
    gym_id: UUID,
    *,
    limit: int,
    offset: int = 0,
    by_user_id: UUID | None = None,
) -> tuple[list[ActivityItem], bool]:
    """(items, whether more follow), newest first.

    Each source is read up to offset + limit + 1 rows and the three are
    merged: plenty for a gym's log, without a database UNION over unlike
    tables.
    """

    window = offset + limit + 1
    staff = aliased(UserProfile)

    check_in_query = (
        select(GymCheckIn, GymMember.full_name, staff.full_name)
        .outerjoin(GymMember, GymMember.id == GymCheckIn.member_id)
        .outerjoin(staff, staff.user_id == GymCheckIn.checked_in_by_user_id)
        .where(GymCheckIn.gym_id == gym_id)
    )
    payment_query = (
        select(Payment, GymMembership, GymMember.full_name, staff.full_name)
        .join(GymMembership, GymMembership.id == Payment.membership_id)
        .join(GymMember, GymMember.id == GymMembership.member_id)
        .outerjoin(staff, staff.user_id == Payment.recorded_by_user_id)
        .where(
            Payment.gym_id == gym_id,
            Payment.status == PaymentStatus.COMPLETED,
        )
    )
    added_query = (
        select(GymMember, staff.full_name)
        .outerjoin(staff, staff.user_id == GymMember.added_by_user_id)
        .where(
            GymMember.gym_id == gym_id,
            # An archived member (e.g. added by mistake) isn't news.
            GymMember.status == GymMemberStatus.ACTIVE,
        )
    )
    if by_user_id is not None:
        check_in_query = check_in_query.where(
            GymCheckIn.checked_in_by_user_id == by_user_id
        )
        payment_query = payment_query.where(Payment.recorded_by_user_id == by_user_id)
        added_query = added_query.where(GymMember.added_by_user_id == by_user_id)

    check_ins = (
        await session.execute(
            check_in_query.order_by(GymCheckIn.checked_in_at.desc()).limit(window)
        )
    ).all()
    payments = (
        await session.execute(
            payment_query.order_by(Payment.paid_at.desc()).limit(window)
        )
    ).all()
    added = (
        await session.execute(
            added_query.order_by(GymMember.created_at.desc()).limit(window)
        )
    ).all()

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
            by_user_id=check_in.checked_in_by_user_id,
            by_name=_name(by),
        )
        for check_in, name, by in check_ins
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
            by_user_id=payment.recorded_by_user_id,
            by_name=_name(by),
        )
        for payment, membership, name, by in payments
    ]
    items += [
        ActivityItem(
            kind="member_added",
            at=member.created_at,
            member_id=member.id,
            member_name=member.full_name,
            detail="New member",
            ok=True,
            by_user_id=member.added_by_user_id,
            by_name=_name(by),
        )
        for member, by in added
    ]
    items.sort(key=lambda item: item.at, reverse=True)
    page = items[offset : offset + limit + 1]
    return page[:limit], len(page) > limit


@dataclass(frozen=True)
class StaffDay:
    """What one staff member did today, for the owner's end-of-day check."""

    payments: int = 0
    cash: Decimal = Decimal(0)
    mpesa: Decimal = Decimal(0)
    check_ins: int = 0


async def staff_day(
    session: AsyncSession, gym_id: UUID, *, start: datetime, end: datetime
) -> dict[UUID, StaffDay]:
    """Completed payments (cash and M-Pesa) and allowed check-ins per staff
    member between start and end."""

    paid_at = func.coalesce(Payment.paid_at, Payment.created_at)
    payment_rows = (
        await session.execute(
            select(
                Payment.recorded_by_user_id,
                Payment.method,
                func.count(),
                func.coalesce(func.sum(Payment.amount), 0),
            )
            .where(
                Payment.gym_id == gym_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.recorded_by_user_id.is_not(None),
                paid_at >= start,
                paid_at < end,
            )
            .group_by(Payment.recorded_by_user_id, Payment.method)
        )
    ).all()
    check_in_rows = (
        await session.execute(
            select(GymCheckIn.checked_in_by_user_id, func.count())
            .where(
                GymCheckIn.gym_id == gym_id,
                GymCheckIn.result == CheckInResult.ALLOWED,
                GymCheckIn.checked_in_by_user_id.is_not(None),
                GymCheckIn.checked_in_at >= start,
                GymCheckIn.checked_in_at < end,
            )
            .group_by(GymCheckIn.checked_in_by_user_id)
        )
    ).all()

    days: dict[UUID, StaffDay] = {}
    for user_id, method, count, amount in payment_rows:
        day = days.get(user_id, StaffDay())
        days[user_id] = StaffDay(
            payments=day.payments + count,
            cash=day.cash + (amount if method == PaymentMethod.CASH else 0),
            mpesa=day.mpesa + (amount if method == PaymentMethod.MPESA else 0),
            check_ins=day.check_ins,
        )
    for user_id, count in check_in_rows:
        day = days.get(user_id, StaffDay())
        days[user_id] = StaffDay(
            payments=day.payments, cash=day.cash, mpesa=day.mpesa, check_ins=count
        )
    return days
