"""Choosing the channel for a sign-in code and sending it through that channel.

Policy (D-011): numbers from ``OTP_SMS_REGIONS`` (Kenya) get the code by SMS;
numbers from every other supported country get it on WhatsApp. There is no
fallback between channels yet. Adding one later means trying the next channel
in ``OTPDelivery.send``; the authentication service does not change.
"""

import asyncio
from typing import Annotated

import phonenumbers
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.integrations.delivery import OTPSender
from app.integrations.sms.base import SMSProvider
from app.integrations.sms.dependencies import get_sms_provider
from app.integrations.whatsapp.base import WhatsAppOTPProvider
from app.integrations.whatsapp.dependencies import get_whatsapp_provider
from app.modules.auth.enums import OTPDeliveryChannel
from app.modules.auth.exceptions import (
    InvalidPhoneNumberError,
    OTPChannelUnavailableError,
)


class OTPDelivery:
    """Routes sign-in codes to the SMS or WhatsApp provider by country."""

    def __init__(
        self,
        *,
        settings: Settings,
        sms_provider: SMSProvider,
        whatsapp_provider: WhatsAppOTPProvider | None,
    ) -> None:
        self._supported_regions = frozenset(settings.otp_supported_regions)
        self._sms_regions = frozenset(settings.otp_sms_regions)
        self._senders: dict[OTPDeliveryChannel, tuple[OTPSender | None, float]] = {
            OTPDeliveryChannel.SMS: (
                sms_provider,
                settings.sms_send_timeout_seconds,
            ),
            OTPDeliveryChannel.WHATSAPP: (
                whatsapp_provider,
                settings.whatsapp_send_timeout_seconds,
            ),
        }

    def channel_for(self, phone_number: str) -> OTPDeliveryChannel:
        """Return the channel for an E.164 number from a supported country.

        Raises InvalidPhoneNumberError for countries SWETO doesn't serve yet,
        and OTPChannelUnavailableError when that channel has no provider, so
        no challenge is created for a code that can't be sent.
        """

        region = phonenumbers.region_code_for_number(phonenumbers.parse(phone_number))
        if region not in self._supported_regions:
            raise InvalidPhoneNumberError(
                "SWETO sign-in isn't available for numbers from this country yet."
            )
        channel = (
            OTPDeliveryChannel.SMS
            if region in self._sms_regions
            else OTPDeliveryChannel.WHATSAPP
        )
        if self._senders[channel][0] is None:
            raise OTPChannelUnavailableError(channel=channel)
        return channel

    async def send(
        self,
        *,
        channel: OTPDeliveryChannel,
        phone_number: str,
        otp_code: str,
        expires_in_seconds: int,
    ) -> None:
        """Send through the channel's provider within its timeout.

        Raises TimeoutError, OTPDeliveryError or whatever the provider raised;
        the caller records the failure. Never retries on another channel.
        """

        sender, timeout_seconds = self._senders[channel]
        if sender is None:
            raise OTPChannelUnavailableError(channel=channel)
        async with asyncio.timeout(timeout_seconds):
            await sender.send_otp(
                phone_number=phone_number,
                otp_code=otp_code,
                expires_in_seconds=expires_in_seconds,
            )


def get_otp_delivery(
    settings: Annotated[Settings, Depends(get_settings)],
    sms_provider: Annotated[SMSProvider, Depends(get_sms_provider)],
    whatsapp_provider: Annotated[
        WhatsAppOTPProvider | None, Depends(get_whatsapp_provider)
    ],
) -> OTPDelivery:
    """FastAPI dependency wiring the configured providers into OTPDelivery."""

    return OTPDelivery(
        settings=settings,
        sms_provider=sms_provider,
        whatsapp_provider=whatsapp_provider,
    )
