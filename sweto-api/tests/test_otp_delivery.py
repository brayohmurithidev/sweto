"""Unit tests for OTP channel policy and routing (no database, no providers)."""

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations.whatsapp.base import WhatsAppDeliveryError
from app.modules.auth.enums import OTPDeliveryChannel
from app.modules.auth.exceptions import (
    InvalidPhoneNumberError,
    OTPChannelUnavailableError,
)
from app.modules.auth.otp_delivery import OTPDelivery

_REQUIRED = {
    "database_url": "postgresql+asyncpg://sweto:pw@localhost:5432/sweto",
    "otp_hash_secret": "test-otp-secret-that-is-long-enough-for-secure-hmac",
    "jwt_secret_key": "test-jwt-secret-that-is-at-least-thirty-two-bytes",
}


def delivery(
    *, whatsapp: AsyncMock | None = None, **settings: object
) -> tuple[OTPDelivery, AsyncMock, AsyncMock | None]:
    sms = AsyncMock()
    whatsapp_provider = AsyncMock() if whatsapp is None else whatsapp
    return (
        OTPDelivery(
            settings=Settings(**_REQUIRED, **settings),
            sms_provider=sms,
            whatsapp_provider=whatsapp_provider,
        ),
        sms,
        whatsapp_provider,
    )


@pytest.mark.parametrize(
    ("phone", "channel"),
    [
        ("+254712345678", OTPDeliveryChannel.SMS),  # Kenya, 7-series
        ("+254112345678", OTPDeliveryChannel.SMS),  # Kenya, 1-series
        ("+256701234567", OTPDeliveryChannel.WHATSAPP),  # Uganda
        ("+255712345678", OTPDeliveryChannel.WHATSAPP),  # Tanzania
        ("+250781234567", OTPDeliveryChannel.WHATSAPP),  # Rwanda
        ("+25779123456", OTPDeliveryChannel.WHATSAPP),  # Burundi
    ],
)
def test_channel_is_chosen_by_country(phone: str, channel: OTPDeliveryChannel) -> None:
    otp_delivery, _, _ = delivery()
    assert otp_delivery.channel_for(phone) is channel


def test_unsupported_country_is_rejected() -> None:
    otp_delivery, _, _ = delivery()
    with pytest.raises(InvalidPhoneNumberError, match="this country"):
        otp_delivery.channel_for("+12025550123")


def test_sms_countries_are_configurable() -> None:
    otp_delivery, _, _ = delivery(otp_sms_regions=["KE", "UG"])
    assert otp_delivery.channel_for("+256701234567") is OTPDeliveryChannel.SMS


def test_missing_whatsapp_provider_makes_the_channel_unavailable() -> None:
    otp_delivery = OTPDelivery(
        settings=Settings(**_REQUIRED),
        sms_provider=AsyncMock(),
        whatsapp_provider=None,
    )
    with pytest.raises(OTPChannelUnavailableError) as raised:
        otp_delivery.channel_for("+256701234567")
    assert raised.value.channel is OTPDeliveryChannel.WHATSAPP
    assert otp_delivery.channel_for("+254712345678") is OTPDeliveryChannel.SMS


async def test_send_uses_only_the_channels_provider() -> None:
    otp_delivery, sms, whatsapp = delivery()

    await otp_delivery.send(
        channel=OTPDeliveryChannel.WHATSAPP,
        phone_number="+256701234567",
        otp_code="123456",
        expires_in_seconds=300,
    )

    assert whatsapp is not None
    whatsapp.send_otp.assert_awaited_once_with(
        phone_number="+256701234567", otp_code="123456", expires_in_seconds=300
    )
    sms.send_otp.assert_not_awaited()


async def test_whatsapp_failure_does_not_fall_back_to_sms() -> None:
    failing = AsyncMock()
    failing.send_otp.side_effect = WhatsAppDeliveryError("provider_rejected")
    otp_delivery, sms, _ = delivery(whatsapp=failing)

    with pytest.raises(WhatsAppDeliveryError):
        await otp_delivery.send(
            channel=OTPDeliveryChannel.WHATSAPP,
            phone_number="+256701234567",
            otp_code="123456",
            expires_in_seconds=300,
        )

    sms.send_otp.assert_not_awaited()


def test_regions_must_be_known_country_codes() -> None:
    with pytest.raises(ValidationError, match="unknown: XX"):
        Settings(**_REQUIRED, otp_supported_regions=["KE", "XX"])


def test_sms_regions_must_be_supported() -> None:
    with pytest.raises(ValidationError, match="not supported: NG"):
        Settings(**_REQUIRED, otp_sms_regions=["KE", "NG"])


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_console_whatsapp_provider_is_refused_where_real_users_sign_in(
    environment: str,
) -> None:
    # Checked on its own: the console SMS guard would fail first, because no
    # production SMS provider exists until the Advanta adapter is written.
    settings = Settings.model_construct(
        app_environment=environment, whatsapp_provider="console"
    )
    with pytest.raises(ValueError, match="WHATSAPP_PROVIDER=console"):
        settings.validate_whatsapp_provider()

    allowed = Settings.model_construct(
        app_environment="development", whatsapp_provider="console"
    )
    assert allowed.validate_whatsapp_provider() is allowed


def test_whatsapp_is_disabled_by_default() -> None:
    assert Settings.model_fields["whatsapp_provider"].default == "disabled"
