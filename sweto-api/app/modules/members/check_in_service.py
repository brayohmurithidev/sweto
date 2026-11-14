"""Check-in at the door, and the check-in codes members show there."""

from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.auth.exceptions import AuthenticationRateLimitError
from app.modules.gyms.exceptions import GymAccessDeniedError, GymNotFoundError
from app.modules.gyms.models import Gym
from app.modules.gyms.repository import GymRepository, GymStaffRepository
from app.modules.members.codes import (
    display_code,
    generate_code,
    hash_code,
    normalize_code,
    qr_payload,
)
from app.modules.members.enums import (
    CheckInResult,
    GymMembershipStatus,
    GymMemberStatus,
)
from app.modules.members.exceptions import (
    GymMemberArchivedError,
    GymMemberNotFoundError,
)
from app.modules.members.models import GymCheckIn, GymMember, GymMembership
from app.modules.members.notifier import MemberNotifier
from app.modules.members.schemas import (
    CheckInCodeData,
    CheckInData,
    CheckInDayData,
    CheckInLogEntry,
    CheckInMemberData,
    CheckInMembershipData,
)
from app.modules.members.service import MEMBER_MANAGERS, standing_for
from app.rate_limit.base import RateLimiter
from app.shared.clock import Clock

_CODE_ATTEMPTS = 3


def local_day_bounds(day: date, timezone: str) -> tuple[datetime, datetime]:
    """[start, end) of a gym-local calendar day as aware datetimes."""

    start = datetime.combine(day, time.min, tzinfo=ZoneInfo(timezone))
    return start, start + timedelta(days=1)


class CheckInService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        clock: Clock,
        settings: Settings,
        rate_limiter: RateLimiter,
        notifier: MemberNotifier | None = None,
    ) -> None:
        self.session = session
        self.clock = clock
        self.settings = settings
        self.rate_limiter = rate_limiter
        self.notifier = notifier
        self.gyms = GymRepository(session)
        self.staff = GymStaffRepository(session)

    async def issue_code(
        self, *, user_id: UUID, gym_id: UUID, member_id: UUID
    ) -> CheckInCodeData:
        """Give the member a new code; the previous one stops working."""

        gym = await self._gym_for_staff(user_id=user_id, gym_id=gym_id, managers=True)
        for attempt in range(_CODE_ATTEMPTS):
            member = await self._member(gym, member_id)
            if member.status == GymMemberStatus.ARCHIVED:
                raise GymMemberArchivedError(
                    "This member is archived. Restore them before issuing a code."
                )
            code = generate_code()
            member.check_in_code_hash = self._hash(code)
            try:
                await self.session.commit()
            except IntegrityError:
                # Another member of this gym drew the same code: draw again.
                await self.session.rollback()
                if attempt == _CODE_ATTEMPTS - 1:
                    raise
                continue
            sms = None
            if self.notifier is not None:
                sms = await self.notifier.check_in_code(
                    gym=gym, member=member, code=display_code(code)
                )
            return CheckInCodeData(
                member_id=member.id,
                code=display_code(code),
                qr_payload=qr_payload(code),
                sms=sms,
            )
        raise AssertionError("unreachable")  # pragma: no cover

    async def check_in(
        self, *, user_id: UUID, gym_id: UUID, raw_code: str
    ) -> CheckInData:
        gym = await self._gym_for_staff(user_id=user_id, gym_id=gym_id, managers=False)
        await self._enforce_rate_limit(gym.id)

        now = self.clock()
        today = now.astimezone(ZoneInfo(gym.timezone)).date()
        code = normalize_code(raw_code)
        member = None
        if code is not None:
            member = await self.session.scalar(
                select(GymMember).where(
                    GymMember.gym_id == gym.id,
                    GymMember.check_in_code_hash == self._hash(code),
                )
            )

        result, membership, repeat, visits_used = await self._decide(gym, member, today)
        entry = GymCheckIn(
            gym_id=gym.id,
            member_id=member.id if member else None,
            membership_id=membership.id if membership else None,
            result=result,
            repeat_visit=repeat,
            checked_in_at=now,
            checked_in_by_user_id=user_id,
        )
        self.session.add(entry)
        await self.session.commit()

        paid_until = await self._paid_until(member.id) if member else None
        if result == CheckInResult.ALLOWED and not repeat:
            visits_used += 1
        return CheckInData(
            id=entry.id,
            result=result,
            allowed=result == CheckInResult.ALLOWED,
            already_checked_in_today=repeat,
            message=self._message(result, member, membership, paid_until, repeat),
            checked_in_at=now,
            member=None
            if member is None
            else CheckInMemberData(
                id=member.id,
                full_name=member.full_name,
                standing=standing_for(paid_until, today),
                paid_until=paid_until,
            ),
            membership=None
            if membership is None
            else CheckInMembershipData(
                plan_name=membership.plan_name,
                starts_on=membership.starts_on,
                ends_on=membership.ends_on,
                visit_limit=membership.visit_limit,
                visits_used=visits_used,
            ),
        )

    async def day(
        self, *, user_id: UUID, gym_id: UUID, day: date | None
    ) -> CheckInDayData:
        gym = await self._gym_for_staff(user_id=user_id, gym_id=gym_id, managers=False)
        local_day = day or self.clock().astimezone(ZoneInfo(gym.timezone)).date()
        start, end = local_day_bounds(local_day, gym.timezone)
        rows = (
            await self.session.execute(
                select(GymCheckIn, GymMember.full_name)
                .outerjoin(GymMember, GymMember.id == GymCheckIn.member_id)
                .where(
                    GymCheckIn.gym_id == gym.id,
                    GymCheckIn.checked_in_at >= start,
                    GymCheckIn.checked_in_at < end,
                )
                .order_by(GymCheckIn.checked_in_at.desc())
            )
        ).all()
        entries = [
            CheckInLogEntry(
                id=check_in.id,
                result=check_in.result,
                already_checked_in_today=check_in.repeat_visit,
                checked_in_at=check_in.checked_in_at,
                member_id=check_in.member_id,
                member_name=name,
            )
            for check_in, name in rows
        ]
        allowed = [e for e in entries if e.result == CheckInResult.ALLOWED]
        return CheckInDayData(
            date=local_day,
            visits=sum(not e.already_checked_in_today for e in allowed),
            refused=len(entries) - len(allowed),
            check_ins=entries,
        )

    async def _decide(
        self, gym: Gym, member: GymMember | None, today: date
    ) -> tuple[CheckInResult, GymMembership | None, bool, int]:
        """Result, the membership it was judged on, repeat flag, visits used."""

        if member is None:
            return CheckInResult.UNKNOWN_CODE, None, False, 0
        if member.status == GymMemberStatus.ARCHIVED:
            return CheckInResult.ARCHIVED, None, False, 0

        paid = list(
            await self.session.scalars(
                select(GymMembership)
                .where(
                    GymMembership.member_id == member.id,
                    GymMembership.status == GymMembershipStatus.ACTIVE,
                )
                .order_by(GymMembership.starts_on)
            )
        )
        current = next((m for m in paid if m.starts_on <= today <= m.ends_on), None)
        if current is None:
            upcoming = next((m for m in paid if m.starts_on > today), None)
            if upcoming is not None:
                return CheckInResult.NOT_STARTED, upcoming, False, 0
            if paid:
                return CheckInResult.EXPIRED, paid[-1], False, 0
            return CheckInResult.NO_MEMBERSHIP, None, False, 0

        start, end = local_day_bounds(today, gym.timezone)
        already_today = await self.session.scalar(
            select(func.count())
            .select_from(GymCheckIn)
            .where(
                GymCheckIn.member_id == member.id,
                GymCheckIn.result == CheckInResult.ALLOWED,
                GymCheckIn.checked_in_at >= start,
                GymCheckIn.checked_in_at < end,
            )
        )
        visits_used = (
            await self.session.scalar(
                select(func.count())
                .select_from(GymCheckIn)
                .where(
                    GymCheckIn.membership_id == current.id,
                    GymCheckIn.result == CheckInResult.ALLOWED,
                    GymCheckIn.repeat_visit.is_(False),
                )
            )
            or 0
        )
        if already_today:
            # Back the same day (left a bag, second session): let in, no new visit.
            return CheckInResult.ALLOWED, current, True, visits_used
        if current.visit_limit is not None and visits_used >= current.visit_limit:
            return CheckInResult.VISIT_LIMIT_REACHED, current, False, visits_used
        return CheckInResult.ALLOWED, current, False, visits_used

    @staticmethod
    def _message(
        result: CheckInResult,
        member: GymMember | None,
        membership: GymMembership | None,
        paid_until: date | None,
        repeat: bool,
    ) -> str:
        name = member.full_name if member else ""
        if result == CheckInResult.ALLOWED:
            return (
                f"{name} already checked in today." if repeat else f"Welcome, {name}."
            )
        if result == CheckInResult.EXPIRED and paid_until is not None:
            return f"{name}'s membership ended on {paid_until:%d %b %Y}."
        if result == CheckInResult.NOT_STARTED and membership is not None:
            return f"{name}'s membership starts on {membership.starts_on:%d %b %Y}."
        if result == CheckInResult.VISIT_LIMIT_REACHED and membership is not None:
            return f"{name} has used all {membership.visit_limit} visits on this plan."
        return {
            CheckInResult.NO_MEMBERSHIP: f"{name} has no paid membership.",
            CheckInResult.ARCHIVED: f"{name} is archived. Restore them to let them in.",
            CheckInResult.UNKNOWN_CODE: "Code not recognised. Check it and try again.",
        }.get(result, "Not allowed in.")

    async def _paid_until(self, member_id: UUID) -> date | None:
        paid_until: date | None = await self.session.scalar(
            select(func.max(GymMembership.ends_on)).where(
                GymMembership.member_id == member_id,
                GymMembership.status == GymMembershipStatus.ACTIVE,
            )
        )
        return paid_until

    async def _enforce_rate_limit(self, gym_id: UUID) -> None:
        result = await self.rate_limiter.consume(
            key=f"check-in:gym:{gym_id}",
            limit=self.settings.check_in_attempt_limit,
            window_seconds=self.settings.check_in_attempt_window_seconds,
        )
        if not result.allowed:
            raise AuthenticationRateLimitError(
                code="CHECK_IN_RATE_LIMITED",
                message="Too many check-in attempts. Wait a moment and try again.",
                retry_after_seconds=result.retry_after_seconds,
                limit=result.limit,
            )

    def _hash(self, code: str) -> str:
        return hash_code(code, secret=self.settings.otp_hash_secret)

    async def _gym_for_staff(
        self, *, user_id: UUID, gym_id: UUID, managers: bool
    ) -> Gym:
        staff = await self.staff.get_user_membership(user_id=user_id, gym_id=gym_id)
        if staff is None:
            raise GymAccessDeniedError("You do not have access to this gym.")
        if managers and staff.role not in MEMBER_MANAGERS:
            raise GymAccessDeniedError(
                "Only the gym's owner or a manager can issue check-in codes."
            )
        gym = await self.gyms.get_by_id(gym_id)
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")
        return gym

    async def _member(self, gym: Gym, member_id: UUID) -> GymMember:
        member = await self.session.scalar(
            select(GymMember)
            .where(GymMember.id == member_id, GymMember.gym_id == gym.id)
            .with_for_update()
        )
        if member is None:
            raise GymMemberNotFoundError("This member was not found in your gym.")
        return member
