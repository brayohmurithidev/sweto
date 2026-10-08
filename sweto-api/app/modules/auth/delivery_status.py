"""Applying provider delivery reports to OTP challenges.

Rules:
- Delivery status only moves forward: accepted -> sent -> delivered -> read.
  Duplicates and late, older statuses are ignored, so webhooks can be
  retried or arrive out of order safely.
- ``failed`` is final, and is ignored once the code was delivered.
- A delivery report never makes a code usable. The only change to the
  authentication state is that a failed delivery retires a still-pending
  challenge (status ``expired``): the code never reached the user, and this
  lets them request a new one without waiting for the resend cooldown.
  Verified, expired or blocked challenges are left exactly as they are.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.whatsapp.webhook import WhatsAppStatusEvent
from app.modules.auth.audit import AuthAuditLogger
from app.modules.auth.enums import (
    AuthEventOutcome,
    AuthEventType,
    OTPDeliveryChannel,
    OTPDeliveryStatus,
    OTPStatus,
)
from app.modules.auth.models import OTPChallenge

logger = logging.getLogger(__name__)

_PROGRESS = {
    OTPDeliveryStatus.PENDING: 0,
    OTPDeliveryStatus.ACCEPTED: 1,
    OTPDeliveryStatus.SENT: 2,
    OTPDeliveryStatus.DELIVERED: 3,
    OTPDeliveryStatus.READ: 4,
}


@dataclass
class DeliveryUpdateResult:
    applied: int = 0
    ignored: int = 0
    unmatched: int = 0


class DeliveryStatusService:
    """Applies WhatsApp status events to the challenges they belong to."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_logger = AuthAuditLogger(session)

    async def apply_whatsapp_events(
        self, events: list[WhatsAppStatusEvent]
    ) -> DeliveryUpdateResult:
        result = DeliveryUpdateResult()
        now = datetime.now(UTC)
        for event in events:
            challenge = await self._challenge_for(event.message_id)
            if challenge is None:
                result.unmatched += 1
                continue
            if self._apply(challenge, event, now):
                result.applied += 1
            else:
                result.ignored += 1
        await self.session.commit()
        if result.unmatched or result.applied:
            logger.info(
                "WhatsApp delivery reports: applied=%s ignored=%s unmatched=%s",
                result.applied,
                result.ignored,
                result.unmatched,
            )
        return result

    async def _challenge_for(self, message_id: str) -> OTPChallenge | None:
        statement = (
            select(OTPChallenge)
            .where(
                OTPChallenge.provider_message_id == message_id,
                OTPChallenge.delivery_channel == OTPDeliveryChannel.WHATSAPP,
            )
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    def _apply(
        self, challenge: OTPChallenge, event: WhatsAppStatusEvent, now: datetime
    ) -> bool:
        current = challenge.delivery_status
        if current is OTPDeliveryStatus.FAILED:
            return False

        if event.status == "failed":
            if current in {OTPDeliveryStatus.DELIVERED, OTPDeliveryStatus.READ}:
                return False
            challenge.delivery_status = OTPDeliveryStatus.FAILED
            challenge.delivery_status_updated_at = now
            challenge.delivery_error_code = event.error_code
            retired = challenge.status is OTPStatus.PENDING
            if retired:
                challenge.status = OTPStatus.EXPIRED
            self.audit_logger.record(
                event_type=AuthEventType.OTP_DELIVERY_FAILED,
                outcome=AuthEventOutcome.FAILURE,
                challenge_id=challenge.id,
                phone_number=challenge.phone_number,
                metadata={
                    "reason": "undeliverable",
                    "retryable": False,
                    "channel": challenge.delivery_channel.value,
                    "provider_code": event.error_code,
                    "source": "webhook",
                    "challenge_retired": retired,
                },
            )
            return True

        new = OTPDeliveryStatus(event.status)
        if _PROGRESS[new] <= _PROGRESS[current]:
            return False
        challenge.delivery_status = new
        challenge.delivery_status_updated_at = now
        return True
