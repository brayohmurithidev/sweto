import re
from collections.abc import Sequence
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import ColumnElement, Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.gyms.models import GymMembershipPlan
from app.modules.members.enums import (
    GymMembershipStatus,
    GymMemberStatus,
    MemberStanding,
)
from app.modules.members.models import GymMember, GymMembership
from app.modules.members.periods import EXPIRING_WITHIN_DAYS


def paid_until_column() -> ColumnElement[date]:
    """Last day covered by any paid membership of the outer ``GymMember``."""

    return (
        select(func.max(GymMembership.ends_on))
        .where(
            GymMembership.member_id == GymMember.id,
            GymMembership.status == GymMembershipStatus.ACTIVE,
        )
        .correlate(GymMember)
        .scalar_subquery()
    )


def current_start_column(today: date) -> ColumnElement[date]:
    """First day of the outer member's period covering ``today``, or of the
    next paid one when it hasn't started yet (pay Friday, start Monday)."""

    return (
        select(func.min(GymMembership.starts_on))
        .where(
            GymMembership.member_id == GymMember.id,
            GymMembership.status == GymMembershipStatus.ACTIVE,
            GymMembership.ends_on >= today,
        )
        .correlate(GymMember)
        .scalar_subquery()
    )


def _search_condition(search: str) -> ColumnElement[bool]:
    term = search.strip()
    conditions: list[ColumnElement[bool]] = [GymMember.full_name.ilike(f"%{term}%")]
    digits = re.sub(r"\D", "", term)
    # "0712 345" typed locally matches "+254712345..." stored.
    digits = digits.removeprefix("0")
    if len(digits) >= 3:
        conditions.append(GymMember.phone_number.contains(digits))
    return or_(*conditions)


def _standing_condition(
    paid_until: ColumnElement[date],
    starts_on: ColumnElement[date],
    standing: MemberStanding,
    today: date,
) -> ColumnElement[bool]:
    last_expiring_day = today + timedelta(days=EXPIRING_WITHIN_DAYS - 1)
    if standing == MemberStanding.ACTIVE:
        # Paid through today or later, including members starting soon: the
        # list's Active tab is everyone who has paid.
        return paid_until >= today
    if standing == MemberStanding.EXPIRING:
        return and_(paid_until.between(today, last_expiring_day), starts_on <= today)
    if standing == MemberStanding.UPCOMING:
        return starts_on > today
    if standing == MemberStanding.EXPIRED:
        return paid_until < today
    return paid_until.is_(None)


class GymMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, member: GymMember) -> None:
        self.session.add(member)

    async def get(
        self, *, gym_id: UUID, member_id: UUID, for_update: bool = False
    ) -> GymMember | None:
        statement = select(GymMember).where(
            GymMember.id == member_id, GymMember.gym_id == gym_id
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_with_history(
        self, *, gym_id: UUID, member_id: UUID
    ) -> GymMember | None:
        statement = (
            select(GymMember)
            .options(
                selectinload(GymMember.memberships).selectinload(GymMembership.payments)
            )
            .where(GymMember.id == member_id, GymMember.gym_id == gym_id)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def phone_taken(
        self, *, gym_id: UUID, phone_number: str, excluding: UUID | None = None
    ) -> bool:
        statement = select(GymMember.id).where(
            GymMember.gym_id == gym_id, GymMember.phone_number == phone_number
        )
        if excluding is not None:
            statement = statement.where(GymMember.id != excluding)
        result = await self.session.execute(statement.limit(1))
        return result.first() is not None

    async def current_start(self, member_id: UUID, today: date) -> date | None:
        """First day of the period covering ``today``, or of the next one."""

        start: date | None = await self.session.scalar(
            select(func.min(GymMembership.starts_on)).where(
                GymMembership.member_id == member_id,
                GymMembership.status == GymMembershipStatus.ACTIVE,
                GymMembership.ends_on >= today,
            )
        )
        return start

    async def paid_until(self, member_id: UUID) -> date | None:
        statement = select(func.max(GymMembership.ends_on)).where(
            GymMembership.member_id == member_id,
            GymMembership.status == GymMembershipStatus.ACTIVE,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        gym_id: UUID,
        status: GymMemberStatus,
        today: date,
        search: str | None,
        standing: MemberStanding | None,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[tuple[GymMember, date | None, date | None]], int]:
        paid_until = paid_until_column()
        starts_on = current_start_column(today)
        filtered: Select[tuple[GymMember, date, date]] = select(
            GymMember, paid_until.label("paid_until"), starts_on.label("starts_on")
        ).where(GymMember.gym_id == gym_id, GymMember.status == status)
        if search and search.strip():
            filtered = filtered.where(_search_condition(search))
        if standing is not None:
            filtered = filtered.where(
                _standing_condition(paid_until, starts_on, standing, today)
            )

        total = await self.session.scalar(
            select(func.count()).select_from(filtered.subquery())
        )
        page = await self.session.execute(
            filtered.order_by(func.lower(GymMember.full_name), GymMember.id)
            .limit(limit)
            .offset(offset)
        )
        rows = [(member, until, start) for member, until, start in page.tuples().all()]
        return rows, total or 0


class MembershipPlanLookup:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, *, gym_id: UUID, plan_id: UUID) -> GymMembershipPlan | None:
        statement = select(GymMembershipPlan).where(
            GymMembershipPlan.id == plan_id, GymMembershipPlan.gym_id == gym_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
