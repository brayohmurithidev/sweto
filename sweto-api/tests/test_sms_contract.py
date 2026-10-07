import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations.sms.base import SMSDeliveryError
from app.integrations.sms.messages import render_otp_message

_REQUIRED = {
    "database_url": "postgresql+asyncpg://sweto:pw@localhost:5432/sweto",
    "otp_hash_secret": "test-otp-secret-that-is-long-enough-for-secure-hmac",
    "jwt_secret_key": "test-jwt-secret-that-is-at-least-thirty-two-bytes",
}


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_console_sms_provider_is_refused_where_real_users_sign_in(
    environment: str,
) -> None:
    with pytest.raises(ValidationError, match="SMS_PROVIDER=console"):
        Settings(**_REQUIRED, app_environment=environment, sms_provider="console")


@pytest.mark.parametrize("environment", ["local", "development", "testing"])
def test_console_sms_provider_is_allowed_for_development(environment: str) -> None:
    settings = Settings(**_REQUIRED, app_environment=environment)
    assert settings.sms_provider == "console"


def test_sms_send_timeout_is_bounded() -> None:
    with pytest.raises(ValidationError):
        Settings(**_REQUIRED, sms_send_timeout_seconds=0)
    with pytest.raises(ValidationError):
        Settings(**_REQUIRED, sms_send_timeout_seconds=120)


def test_otp_message_contains_code_expiry_and_warning() -> None:
    message = render_otp_message(otp_code="482913", expires_in_seconds=300)

    assert message.startswith("482913 is your SWETO verification code.")
    assert "5 minutes" in message
    assert "Never share" in message
    assert len(message) <= 160  # one SMS segment


def test_otp_message_uses_singular_minute() -> None:
    assert "1 minute." in render_otp_message(otp_code="1", expires_in_seconds=60)


def test_delivery_error_is_retryable_by_default() -> None:
    error = SMSDeliveryError("provider_unavailable")
    assert error.retryable is True
    assert str(error) == "provider_unavailable"
