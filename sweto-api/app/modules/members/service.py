from datetime import date, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.phone import normalize_phone_number
from app.modules.gyms.enums import GymStaffRole, MembershipBillingPeriod
from app.modules.gyms.exceptions import GymAccessDeniedError, GymNotFoundError
from app.modules.gyms.models import Gym
from app.modules.gyms.repository import GymRepository, GymStaffRepository
from app.modules.members.enums import (
    GymMembershipStatus,
    GymMemberStatus,
    MemberStanding,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.members.exceptions import (
    GymMemberArchivedError,
    GymMemberNotFoundError,
    GymMemberPhoneTakenError,
    InvalidMembershipPaymentError,
)
from app.modules.members.models import GymMember, GymMembership, Payment
from app.modules.members.periods import EXPIRING_WITHIN_DAYS, period_end
from app.modules.members.repository import GymMemberRepository, MembershipPlanLookup
from app.modules.members.schemas import (
    CreateGymMemberRequest,
    GymMemberData,
    GymMemberDetailData,
    GymMemberListData,
    GymMembershipData,
    PaymentData,
    RecordCashPaymentData,
    RecordCashPaymentRequest,
    UpdateGymMemberRequest,
)
from app.shared.clock import Clock

MEMBER_MANAGERS = frozenset({GymStaffRole.OWNER, GymStaffRole.MANAGER})
BACKDATE_LIMIT_DAYS = 90


def standing_for(paid_until: date | None, today: date) -> MemberStanding:
    if paid_until is None:
        return MemberStanding.NO_MEMBERSHIP
    if paid_until < today:
        return MemberStanding.EXPIRED
    if paid_until < today + timedelta(days=EXPIRING_WITHIN_DAYS):
        return MemberStanding.EXPIRING
    return MemberStanding.ACTIVE


class GymMemberService:
    """Members a gym runs through SWETO: records, memberships, cash payments."""

    def __init__(self, *, session: AsyncSession, clock: Clock) -> None:
        self.session = session
        self.clock = clock
        self.gyms = GymRepository(session)
        self.staff = GymStaffRepository(session)
        self.members = GymMemberRepository(session)
        self.plans = MembershipPlanLookup(session)

    async def list_members(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        status: GymMemberStatus,
        search: str | None,
        standing: MemberStanding | None,
        limit: int,
        offset: int,
    ) -> GymMemberListData:
        gym = await self._gym_for_manager(user_id=user_id, gym_id=gym_id)
        today = self._today(gym)
        rows, total = await self.members.list(
            gym_id=gym.id,
            status=status,
            today=today,
            search=search,
            standing=standing,
            limit=limit,
            offset=offset,
        )
        return GymMemberListData(
            members=[self._member_data(m, until, today) for m, until in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def create_member(
        self, *, user_id: UUID, gym_id: UUID, payload: CreateGymMemberRequest
    ) -> GymMemberData:
        gym = await self._gym_for_manager(user_id=user_id, gym_id=gym_id)
        phone = self._normalize_phone(payload.phone_number, gym)
        if await self.members.phone_taken(gym_id=gym.id, phone_number=phone):
            raise self._phone_taken()
        member = GymMember(
            gym_id=gym.id, full_name=payload.full_name, phone_number=phone
        )
        self.members.add(member)
        await self._commit_member_change()
        await self.session.refresh(member)
        return self._member_data(member, None, self._today(gym))

    async def get_member(
        self, *, user_id: UUID, gym_id: UUID, member_id: UUID
    ) -> GymMemberDetailData:
        gym = await self._gym_for_manager(user_id=user_id, gym_id=gym_id)
        return await self._detail(gym, member_id)

    async def update_member(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        member_id: UUID,
        payload: UpdateGymMemberRequest,
    ) -> GymMemberData:
        gym = await self._gym_for_manager(user_id=user_id, gym_id=gym_id)
        member = await self._member(gym, member_id, for_update=True)
        if payload.full_name is not None:
            member.full_name = payload.full_name
        if payload.phone_number is not None:
            phone = self._normalize_phone(payload.phone_number, gym)
            if await self.members.phone_taken(
                gym_id=gym.id, phone_number=phone, excluding=member.id
            ):
                raise self._phone_taken()
            member.phone_number = phone
        await self._commit_member_change()
        return await self._summary(gym, member)

    async def set_archived(
        self, *, user_id: UUID, gym_id: UUID, member_id: UUID, archived: bool
    ) -> GymMemberData:
        """Archive instead of delete, so payment history survives."""

        gym = await self._gym_for_manager(user_id=user_id, gym_id=gym_id)
        member = await self._member(gym, member_id, for_update=True)
        member.status = GymMemberStatus.ARCHIVED if archived else GymMemberStatus.ACTIVE
        await self.session.commit()
        return await self._summary(gym, member)

    async def record_cash_payment(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        member_id: UUID,
        payload: RecordCashPaymentRequest,
    ) -> RecordCashPaymentData:
        """Record cash received and add the membership period it pays for.

        The period starts the day after the member's latest paid period ends,
        or today if they have lapsed (or never paid), so paying early never
        loses days. The member row is locked so two payments recorded at the
        same moment cannot claim the same dates.
        """

        gym = await self._gym_for_manager(user_id=user_id, gym_id=gym_id)
        member = await self._member(gym, member_id, for_update=True)
        if member.status == GymMemberStatus.ARCHIVED:
            raise GymMemberArchivedError(
                "This member is archived. Restore them before recording a payment."
            )
        plan = await self.plans.get(gym_id=gym.id, plan_id=payload.plan_id)
        if plan is None or not plan.is_active:
            raise InvalidMembershipPaymentError(
                "That membership plan isn't available. Choose an active plan."
            )

        today = self._today(gym)
        paid_until = await self.members.paid_until(member.id)
        starts_on = self._start_date(payload.starts_on, paid_until, today)
        billing_period = MembershipBillingPeriod(plan.billing_period)
        amount = payload.amount if payload.amount is not None else plan.amount

        membership = GymMembership(
            gym_id=gym.id,
            member_id=member.id,
            plan_id=plan.id,
            plan_name=plan.name,
            amount=amount,
            currency=plan.currency,
            billing_period=billing_period,
            starts_on=starts_on,
            ends_on=period_end(starts_on, billing_period),
            status=GymMembershipStatus.ACTIVE,
            visit_limit=plan.visit_limit,
        )
        self.session.add(membership)
        await self.session.flush()
        self.session.add(
            Payment(
                gym_id=gym.id,
                membership_id=membership.id,
                amount=amount,
                currency=plan.currency,
                method=PaymentMethod.CASH,
                status=PaymentStatus.COMPLETED,
                payer_phone=member.phone_number,
                recorded_by_user_id=user_id,
                paid_at=self.clock(),
            )
        )
        await self.session.commit()

        detail = await self._detail(gym, member.id)
        recorded = next(m for m in detail.memberships if m.id == membership.id)
        return RecordCashPaymentData(member=detail.member, membership=recorded)

    @staticmethod
    def _start_date(
        requested: date | None, paid_until: date | None, today: date
    ) -> date:
        covered_today = paid_until is not None and paid_until >= today
        if requested is None:
            if covered_today and paid_until is not None:
                return paid_until + timedelta(days=1)
            return today
        if covered_today:
            raise InvalidMembershipPaymentError(
                "This member already has a current membership. Leave the start "
                "date empty and the new period starts when the current one ends."
            )
        if requested > today:
            raise InvalidMembershipPaymentError(
                "The start date can't be in the future."
            )
        if requested < today - timedelta(days=BACKDATE_LIMIT_DAYS):
            raise InvalidMembershipPaymentError(
                f"The start date can be at most {BACKDATE_LIMIT_DAYS} days ago."
            )
        if paid_until is not None and requested <= paid_until:
            raise InvalidMembershipPaymentError(
                "The start date overlaps a period this member already paid for."
            )
        return requested

    async def _gym_for_manager(self, *, user_id: UUID, gym_id: UUID) -> Gym:
        staff = await self.staff.get_user_membership(user_id=user_id, gym_id=gym_id)
        if staff is None:
            raise GymAccessDeniedError("You do not have access to this gym.")
        if staff.role not in MEMBER_MANAGERS:
            raise GymAccessDeniedError(
                "Only the gym's owner or a manager can manage members."
            )
        gym = await self.gyms.get_by_id(gym_id)
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")
        return gym

    async def _member(
        self, gym: Gym, member_id: UUID, *, for_update: bool = False
    ) -> GymMember:
        member = await self.members.get(
            gym_id=gym.id, member_id=member_id, for_update=for_update
        )
        if member is None:
            raise GymMemberNotFoundError("This member was not found in your gym.")
        return member

    async def _summary(self, gym: Gym, member: GymMember) -> GymMemberData:
        await self.session.refresh(member)
        paid_until = await self.members.paid_until(member.id)
        return self._member_data(member, paid_until, self._today(gym))

    async def _detail(self, gym: Gym, member_id: UUID) -> GymMemberDetailData:
        member = await self.members.get_with_history(gym_id=gym.id, member_id=member_id)
        if member is None:
            raise GymMemberNotFoundError("This member was not found in your gym.")
        today = self._today(gym)
        paid = [
            m.ends_on
            for m in member.memberships
            if m.status == GymMembershipStatus.ACTIVE
        ]
        return GymMemberDetailData(
            member=self._member_data(member, max(paid, default=None), today),
            memberships=[self._membership_data(m, today) for m in member.memberships],
        )

    def _today(self, gym: Gym) -> date:
        """The gym's local date: memberships end at the gym's midnight."""

        return self.clock().astimezone(ZoneInfo(gym.timezone)).date()

    @staticmethod
    def _normalize_phone(phone_number: str, gym: Gym) -> str:
        return normalize_phone_number(
            phone_number, default_region=gym.country_code, require_mobile=True
        )

    @staticmethod
    def _phone_taken() -> GymMemberPhoneTakenError:
        return GymMemberPhoneTakenError(
            "Another member of this gym already uses this phone number. "
            "If they were archived, restore them instead."
        )

    async def _commit_member_change(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            # Two requests adding the same phone at the same moment.
            await self.session.rollback()
            raise self._phone_taken() from error

    @staticmethod
    def _member_data(
        member: GymMember, paid_until: date | None, today: date
    ) -> GymMemberData:
        return GymMemberData(
            id=member.id,
            full_name=member.full_name,
            phone_number=member.phone_number,
            status=member.status,
            standing=standing_for(paid_until, today),
            paid_until=paid_until,
            has_check_in_code=member.check_in_code_hash is not None,
            created_at=member.created_at,
            updated_at=member.updated_at,
        )

    @staticmethod
    def _membership_data(membership: GymMembership, today: date) -> GymMembershipData:
        status = membership.status
        if status == GymMembershipStatus.ACTIVE and membership.ends_on < today:
            status = GymMembershipStatus.EXPIRED
        return GymMembershipData(
            id=membership.id,
            plan_id=membership.plan_id,
            plan_name=membership.plan_name,
            amount=membership.amount,
            currency=membership.currency,
            billing_period=MembershipBillingPeriod(membership.billing_period),
            starts_on=membership.starts_on,
            ends_on=membership.ends_on,
            status=status,
            visit_limit=membership.visit_limit,
            payments=[
                PaymentData(
                    id=p.id,
                    amount=p.amount,
                    currency=p.currency,
                    method=p.method,
                    status=p.status,
                    paid_at=p.paid_at,
                    recorded_by_user_id=p.recorded_by_user_id,
                )
                for p in membership.payments
            ],
        )
