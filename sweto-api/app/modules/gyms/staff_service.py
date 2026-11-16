"""Gym staff: who works at a gym, in which role, and adding or removing them.

Only the owner manages staff. A person works at one gym at a time. Adding
someone creates their SWETO account if they have none; they sign in with
their phone number like everyone else and land in this gym.
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.sms.base import SMSDeliveryError, SMSProvider
from app.modules.auth.enums import UserRole, UserStatus
from app.modules.auth.models import User
from app.modules.auth.phone import normalize_phone_number
from app.modules.auth.repository import RefreshSessionRepository, UserRepository
from app.modules.gyms.enums import GymStaffRole, GymStaffStatus
from app.modules.gyms.exceptions import (
    GymAccessDeniedError,
    GymNotFoundError,
    GymStaffChangeNotAllowedError,
    GymStaffConflictError,
    GymStaffNotFoundError,
)
from app.modules.gyms.models import Gym, GymStaff
from app.modules.gyms.permissions import (
    ASSIGNABLE_ROLES,
    DENIED_MESSAGES,
    GymPermission,
    permissions_for,
    role_can,
)
from app.modules.gyms.repository import GymRepository, GymStaffRepository
from app.modules.gyms.schemas import (
    AddGymStaffData,
    AddGymStaffRequest,
    GymStaffAccessData,
    GymStaffData,
    GymStaffListData,
    GymStaffTodayData,
    UpdateGymStaffRequest,
)
from app.modules.gyms.staff_messages import staff_invite
from app.modules.profiles.models import UserProfile
from app.shared.clock import Clock

logger = logging.getLogger(__name__)


class GymStaffService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        sms: SMSProvider,
        clock: Clock,
        sms_timeout_seconds: float,
    ) -> None:
        self.session = session
        self.sms = sms
        self.clock = clock
        self.sms_timeout_seconds = sms_timeout_seconds
        self.staff = GymStaffRepository(session)
        self.gyms = GymRepository(session)
        self.users = UserRepository(session)
        self.sessions = RefreshSessionRepository(session)

    async def my_access(self, *, user_id: UUID, gym_id: UUID) -> GymStaffAccessData:
        membership = await self.staff.get_user_membership(
            user_id=user_id, gym_id=gym_id
        )
        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")
        return GymStaffAccessData(
            gym_id=gym_id,
            staff_id=membership.id,
            role=membership.role,
            is_primary_owner=membership.is_primary_owner,
            permissions=sorted(p.value for p in permissions_for(membership.role)),
        )

    async def list_staff(self, *, user_id: UUID, gym_id: UUID) -> GymStaffListData:
        gym = await self._gym_for_owner(user_id=user_id, gym_id=gym_id)
        rows = await self.staff.list_for_gym(gym_id)
        # Imported here: the members module builds on the gyms one.
        from app.modules.members.activity import StaffDay, staff_day

        zone = ZoneInfo(gym.timezone)
        start = datetime.combine(self.clock().astimezone(zone).date(), time.min, zone)
        days = await staff_day(
            self.session, gym.id, start=start, end=start + timedelta(days=1)
        )
        staff = []
        for row in rows:
            data = await self._data(row)
            day = days.get(row.user_id, StaffDay())
            data.today = GymStaffTodayData(
                payments=day.payments,
                cash=day.cash,
                mpesa=day.mpesa,
                check_ins=day.check_ins,
            )
            staff.append(data)
        return GymStaffListData(staff=staff)

    async def add_staff(
        self, *, user_id: UUID, gym_id: UUID, payload: AddGymStaffRequest
    ) -> AddGymStaffData:
        gym = await self._gym_for_owner(user_id=user_id, gym_id=gym_id)
        role = self._assignable(payload.role)
        phone = normalize_phone_number(
            payload.phone_number,
            default_region=gym.country_code,
            require_mobile=True,
        )
        name = payload.full_name.strip()

        person = await self.users.get_by_phone_number(phone)
        if person is not None and person.role != UserRole.USER:
            raise GymStaffConflictError(
                "This phone number belongs to a SWETO staff account."
            )
        if person is not None:
            current = await self.staff.find_current_for_user(person.id)
            if current is not None:
                raise GymStaffConflictError(
                    "This person is already on your staff."
                    if current.gym_id == gym.id
                    else "This phone number already works at another gym on SWETO."
                )
        if person is None:
            # Pending until they first sign in with this number.
            person = User(phone_number=phone, status=UserStatus.PENDING)
            self.users.add(person)
            await self.session.flush()

        await self._set_name(person.id, name)

        # Someone removed earlier comes back on their old row.
        membership = await self.staff.get_any(gym_id=gym.id, user_id=person.id)
        if membership is None:
            membership = GymStaff(
                gym_id=gym.id,
                user_id=person.id,
                role=role,
                status=GymStaffStatus.ACTIVE,
                is_primary_owner=False,
            )
            self.staff.add(membership)
        else:
            membership.role = role
            membership.status = GymStaffStatus.ACTIVE
        await self.session.commit()
        await self.session.refresh(membership)

        sent = await self._send_invite(phone=phone, gym=gym, role=role)
        return AddGymStaffData(
            staff=await self._data(membership),
            invite_sms="sent" if sent else "failed",
        )

    async def update_staff(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        staff_id: UUID,
        payload: UpdateGymStaffRequest,
    ) -> GymStaffData:
        await self._gym_for_owner(user_id=user_id, gym_id=gym_id)
        membership = await self._changeable(
            gym_id=gym_id, staff_id=staff_id, actor_id=user_id
        )
        if payload.role is not None:
            membership.role = self._assignable(payload.role)
        if payload.status is not None:
            membership.status = GymStaffStatus(payload.status)
            if membership.status == GymStaffStatus.SUSPENDED:
                await self._sign_out(membership.user_id)
        await self.session.commit()
        await self.session.refresh(membership)
        return await self._data(membership)

    async def remove_staff(
        self, *, user_id: UUID, gym_id: UUID, staff_id: UUID
    ) -> None:
        await self._gym_for_owner(user_id=user_id, gym_id=gym_id)
        membership = await self._changeable(
            gym_id=gym_id, staff_id=staff_id, actor_id=user_id
        )
        membership.status = GymStaffStatus.REMOVED
        await self._sign_out(membership.user_id)
        await self.session.commit()

    async def _gym_for_owner(self, *, user_id: UUID, gym_id: UUID) -> Gym:
        membership = await self.staff.get_user_membership(
            user_id=user_id, gym_id=gym_id
        )
        if membership is None:
            raise GymAccessDeniedError("You do not have access to this gym.")
        if not role_can(membership.role, GymPermission.MANAGE_STAFF):
            raise GymAccessDeniedError(DENIED_MESSAGES[GymPermission.MANAGE_STAFF])
        gym = await self.gyms.get_by_id(gym_id)
        if gym is None:
            raise GymNotFoundError("The requested gym was not found.")
        return gym

    async def _changeable(
        self, *, gym_id: UUID, staff_id: UUID, actor_id: UUID
    ) -> GymStaff:
        membership = await self.staff.get_for_gym(
            gym_id=gym_id, staff_id=staff_id, for_update=True
        )
        if membership is None or membership.status == GymStaffStatus.REMOVED:
            raise GymStaffNotFoundError("This person is not on your staff.")
        if membership.role == GymStaffRole.OWNER or membership.is_primary_owner:
            raise GymStaffChangeNotAllowedError("The gym's owner cannot be changed.")
        if membership.user_id == actor_id:
            raise GymStaffChangeNotAllowedError("You cannot change your own access.")
        return membership

    @staticmethod
    def _assignable(role: GymStaffRole) -> GymStaffRole:
        if role not in ASSIGNABLE_ROLES:
            raise GymStaffChangeNotAllowedError(
                "Staff can be a manager, receptionist or trainer."
            )
        return role

    async def _set_name(self, user_id: UUID, name: str) -> None:
        """Use the owner's name for them unless they already set their own."""

        profile = await self.session.scalar(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        if profile is None:
            self.session.add(UserProfile(user_id=user_id, full_name=name))
        elif not profile.full_name:
            profile.full_name = name

    async def _sign_out(self, user_id: UUID) -> None:
        now: datetime = self.clock()
        await self.sessions.revoke_all_for_user(user_id=user_id, now=now)

    async def _send_invite(self, *, phone: str, gym: Gym, role: GymStaffRole) -> bool:
        try:
            await asyncio.wait_for(
                self.sms.send_text(
                    phone_number=phone,
                    message=staff_invite(gym_name=gym.name, role=role),
                ),
                timeout=self.sms_timeout_seconds,
            )
        except (SMSDeliveryError, TimeoutError):
            logger.warning("Staff invite SMS failed for gym %s", gym.id)
            return False
        return True

    async def _data(self, membership: GymStaff) -> GymStaffData:
        user = await self.session.get(User, membership.user_id)
        profile = await self.session.scalar(
            select(UserProfile).where(UserProfile.user_id == membership.user_id)
        )
        return GymStaffData(
            id=membership.id,
            user_id=membership.user_id,
            full_name=profile.full_name if profile is not None else None,
            phone_number=user.phone_number if user is not None else None,
            role=membership.role,
            status=membership.status,
            is_primary_owner=membership.is_primary_owner,
            has_signed_in=user is not None and user.last_login_at is not None,
            added_at=membership.created_at,
        )
