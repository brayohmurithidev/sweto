"""Sends SMS to members and records each one.

Called after the change it reports has been committed, so a slow or failing
provider can delay the response but never undo a payment or a check-in. Each
send is claimed in member_messages first; the unique indexes there make a
second welcome, receipt or reminder for the same thing a no-op, however many
times (or from however many processes) it is attempted.
"""

import asyncio
import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.sms.base import SMSDeliveryError, SMSProvider
from app.modules.gyms.models import Gym
from app.modules.members import messages
from app.modules.members.enums import MemberMessageKind, MemberMessageStatus
from app.modules.members.models import GymMember, GymMembership, MemberMessage
from app.shared.clock import Clock

logger = logging.getLogger(__name__)


class MemberNotifier:
    def __init__(
        self,
        *,
        session: AsyncSession,
        sms: SMSProvider,
        clock: Clock,
        timeout_seconds: float,
    ) -> None:
        self.session = session
        self.sms = sms
        self.clock = clock
        self.timeout_seconds = timeout_seconds

    async def welcome(
        self,
        *,
        gym: Gym,
        member: GymMember,
        membership: GymMembership,
        code: str,
        starts_on: date | None = None,
    ) -> MemberMessageStatus | None:
        return await self._send(
            gym=gym,
            member=member,
            membership=membership,
            kind=MemberMessageKind.WELCOME,
            body=messages.welcome(
                gym_name=gym.name,
                gym_phone=gym.phone_number,
                code=code,
                paid_until=membership.ends_on,
                starts_on=starts_on,
            ),
        )

    async def payment_receipt(
        self,
        *,
        gym: Gym,
        member: GymMember,
        membership: GymMembership,
        paid_until: date,
        starts_on: date | None = None,
    ) -> MemberMessageStatus | None:
        return await self._send(
            gym=gym,
            member=member,
            membership=membership,
            kind=MemberMessageKind.PAYMENT_RECEIPT,
            body=messages.payment_receipt(
                gym_name=gym.name,
                gym_phone=gym.phone_number,
                amount=membership.amount,
                currency=membership.currency,
                paid_until=paid_until,
                starts_on=starts_on,
            ),
        )

    async def check_in_code(
        self, *, gym: Gym, member: GymMember, code: str
    ) -> MemberMessageStatus | None:
        return await self._send(
            gym=gym,
            member=member,
            membership=None,
            kind=MemberMessageKind.CHECK_IN_CODE,
            body=messages.check_in_code(
                gym_name=gym.name, gym_phone=gym.phone_number, code=code
            ),
        )

    async def expiry_reminder(
        self, *, gym: Gym, member: GymMember, membership: GymMembership, today: date
    ) -> MemberMessageStatus | None:
        kind = (
            MemberMessageKind.EXPIRY_REMINDER_TODAY
            if membership.ends_on == today
            else MemberMessageKind.EXPIRY_REMINDER_3_DAYS
        )
        return await self._send(
            gym=gym,
            member=member,
            membership=membership,
            kind=kind,
            body=messages.expiry_reminder(
                gym_name=gym.name,
                gym_phone=gym.phone_number,
                ends_on=membership.ends_on,
                today=today,
            ),
        )

    async def has_welcome(self, member_id: UUID) -> bool:
        found = await self.session.scalar(
            select(MemberMessage.id).where(
                MemberMessage.member_id == member_id,
                MemberMessage.kind == MemberMessageKind.WELCOME,
            )
        )
        return found is not None

    async def _send(
        self,
        *,
        gym: Gym,
        member: GymMember,
        membership: GymMembership | None,
        kind: MemberMessageKind,
        body: str,
    ) -> MemberMessageStatus | None:
        """Claim, send and record one message. None when nothing was sent."""

        if not member.can_receive_sms:
            return None
        record = MemberMessage(
            gym_id=gym.id,
            member_id=member.id,
            membership_id=membership.id if membership else None,
            kind=kind,
            status=MemberMessageStatus.PENDING,
        )
        try:
            # A savepoint, so a duplicate only undoes this row.
            async with self.session.begin_nested():
                self.session.add(record)
        except IntegrityError:
            # Already sent (or being sent) for this member or period.
            return None
        await self.session.commit()

        try:
            async with asyncio.timeout(self.timeout_seconds):
                message_id = await self.sms.send_text(
                    phone_number=member.phone_number, message=body
                )
        except SMSDeliveryError as error:
            record.status = MemberMessageStatus.FAILED
            record.error_reason = error.reason[:64]
        except TimeoutError:
            record.status = MemberMessageStatus.FAILED
            record.error_reason = "timeout"
        except Exception:
            # Never let a notice break the caller; the record says it failed.
            logger.exception("Member SMS failed unexpectedly: kind=%s", kind)
            record.status = MemberMessageStatus.FAILED
            record.error_reason = "unexpected_error"
        else:
            record.status = MemberMessageStatus.SENT
            record.provider_message_id = message_id
            record.sent_at = self.clock()
        await self.session.commit()
        if record.status == MemberMessageStatus.FAILED:
            logger.warning(
                "Member SMS not sent: kind=%s reason=%s", kind, record.error_reason
            )
        return record.status
