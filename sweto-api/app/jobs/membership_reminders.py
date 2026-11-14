"""Send membership expiry reminders by SMS.

Run it as often as you like (hourly is a good default):

    uv run python -m app.jobs.membership_reminders

A member gets one reminder 3 days before their last paid day and one on that
day, both by the gym's own calendar. Renewed members (another paid period
follows) and members without SMS consent are skipped. Each reminder is
recorded in member_messages before it is sent, so running the job again, or
twice at once, never sends a reminder twice.
"""

import asyncio
import logging
from collections import Counter
from datetime import timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from app.core.config import Settings
from app.integrations.sms.base import SMSProvider
from app.modules.gyms.models import Gym
from app.modules.members.enums import GymMembershipStatus, GymMemberStatus
from app.modules.members.models import GymMember, GymMembership
from app.modules.members.notifier import MemberNotifier
from app.shared.clock import Clock

logger = logging.getLogger(__name__)

REMIND_DAYS_BEFORE = 3


async def send_due_reminders(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    sms: SMSProvider,
    settings: Settings,
    clock: Clock,
) -> Counter[str]:
    """Send every reminder due now; returns counts by outcome."""

    outcomes: Counter[str] = Counter()
    async with session_factory() as session:
        gyms = list(await session.scalars(select(Gym)))
    for gym in gyms:
        today = clock().astimezone(ZoneInfo(gym.timezone)).date()
        due_days = (today, today + timedelta(days=REMIND_DAYS_BEFORE))
        async with session_factory() as session:
            later = aliased(GymMembership)
            rows = (
                await session.execute(
                    select(GymMembership, GymMember)
                    .join(GymMember, GymMember.id == GymMembership.member_id)
                    .where(
                        GymMembership.gym_id == gym.id,
                        GymMembership.status == GymMembershipStatus.ACTIVE,
                        GymMembership.ends_on.in_(due_days),
                        GymMember.status == GymMemberStatus.ACTIVE,
                        GymMember.sms_consent.is_(True),
                        GymMember.sms_opted_out_at.is_(None),
                        # Not renewed: nothing paid ends later.
                        ~exists().where(
                            later.member_id == GymMember.id,
                            later.status == GymMembershipStatus.ACTIVE,
                            later.ends_on > GymMembership.ends_on,
                        ),
                    )
                )
            ).all()
            notifier = MemberNotifier(
                session=session,
                sms=sms,
                clock=clock,
                timeout_seconds=settings.sms_send_timeout_seconds,
            )
            for membership, member in rows:
                status = await notifier.expiry_reminder(
                    gym=gym, member=member, membership=membership, today=today
                )
                outcomes[status.value if status else "already_sent"] += 1
    return outcomes


async def _main() -> None:
    from app.core.config import get_settings
    from app.database.session import async_session_factory
    from app.integrations.sms.dependencies import get_sms_provider
    from app.shared.clock import utc_now

    outcomes = await send_due_reminders(
        session_factory=async_session_factory,
        sms=get_sms_provider(),
        settings=get_settings(),
        clock=utc_now,
    )
    logger.warning("Membership reminders: %s", dict(outcomes) or "none due")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
