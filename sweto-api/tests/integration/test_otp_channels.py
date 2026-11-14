"""OTP channel routing against PostgreSQL (D-011).

Kenyan numbers get the code by SMS; numbers from other supported countries
get it on WhatsApp, with no SMS fallback. Providers are in-memory doubles, so
no WhatsApp credentials are needed.
"""

import pytest

from app.integrations.whatsapp.base import WhatsAppDeliveryError
from app.integrations.whatsapp.dependencies import get_whatsapp_provider
from app.main import app
from tests.integration.conftest import IntegrationAPI

UGANDA = "+256701234567"


async def request_otp(api: IntegrationAPI, phone: str) -> dict:
    response = await api.client.post(
        "/api/v1/auth/request-otp", json={"phone_number": phone}
    )
    return {"status": response.status_code, "body": response.json()}


async def latest_challenge(api: IntegrationAPI) -> list[tuple[object, ...]]:
    return await api.sql(
        "SELECT phone_number, delivery_channel, status FROM otp_challenges "
        "ORDER BY created_at DESC LIMIT 1"
    )


async def test_kenyan_number_gets_the_code_by_sms(api: IntegrationAPI) -> None:
    result = await request_otp(api, "0712345678")

    assert result["status"] == 201
    assert result["body"]["data"]["delivery_channel"] == "sms"
    assert [phone for phone, _ in api.sms.sent] == ["+254712345678"]
    assert api.whatsapp.sent == []
    assert await latest_challenge(api) == [("+254712345678", "sms", "pending")]


@pytest.mark.parametrize(
    ("phone", "e164"),
    [
        ("+256 701 234 567", "+256701234567"),  # Uganda
        ("+255712345678", "+255712345678"),  # Tanzania
        ("+250 78 123 4567", "+250781234567"),  # Rwanda
    ],
)
async def test_other_supported_countries_get_the_code_on_whatsapp(
    api: IntegrationAPI, phone: str, e164: str
) -> None:
    result = await request_otp(api, phone)

    assert result["status"] == 201
    assert result["body"]["data"]["delivery_channel"] == "whatsapp"
    assert result["body"]["data"]["phone_number"] == e164
    assert [sent for sent, _ in api.whatsapp.sent] == [e164]
    assert api.sms.sent == []
    assert await latest_challenge(api) == [(e164, "whatsapp", "pending")]


async def test_whatsapp_code_signs_the_user_in(api: IntegrationAPI) -> None:
    requested = await request_otp(api, UGANDA)

    verified = await api.client.post(
        "/api/v1/auth/verify-otp",
        json={
            "challenge_id": requested["body"]["data"]["challenge_id"],
            "code": api.whatsapp.last_code(),
            "platform": "flutter",
        },
    )

    assert verified.status_code == 200
    assert verified.json()["data"]["user"]["phone_number"] == UGANDA


async def test_unsupported_country_is_rejected_before_any_code(
    api: IntegrationAPI,
) -> None:
    result = await request_otp(api, "+12025550123")

    assert result["status"] == 422
    assert result["body"]["error"]["code"] == "INVALID_PHONE_NUMBER"
    assert api.sms.sent == [] and api.whatsapp.sent == []
    assert await latest_challenge(api) == []


@pytest.mark.parametrize(
    "failure",
    [
        WhatsAppDeliveryError("provider_rejected", retryable=False),
        WhatsAppDeliveryError("provider_unavailable"),
    ],
)
async def test_whatsapp_failure_is_a_clear_error_without_sms_fallback(
    api: IntegrationAPI, failure: WhatsAppDeliveryError
) -> None:
    api.whatsapp.failure = failure

    result = await request_otp(api, UGANDA)

    assert result["status"] == 503
    error = result["body"]["error"]
    assert error["code"] == "OTP_DELIVERY_FAILED"
    assert error["details"] == {"channel": "whatsapp", "retryable": failure.retryable}
    assert "WhatsApp" in error["message"]
    assert api.sms.sent == []
    assert await latest_challenge(api) == [(UGANDA, "whatsapp", "expired")]
    events = await api.sql(
        "SELECT metadata->>'channel', metadata->>'reason' FROM auth_events "
        "WHERE event_type = 'otp_delivery_failed'"
    )
    assert events == [("whatsapp", failure.reason)]


async def test_whatsapp_timeout_does_not_fall_back_to_sms(
    api: IntegrationAPI,
) -> None:
    api.whatsapp.delay_seconds = api.settings.whatsapp_send_timeout_seconds * 5

    result = await request_otp(api, UGANDA)

    assert result["status"] == 503
    assert result["body"]["error"]["details"]["channel"] == "whatsapp"
    assert api.sms.sent == []


async def test_disabled_whatsapp_refuses_before_creating_a_challenge(
    api: IntegrationAPI,
) -> None:
    app.dependency_overrides[get_whatsapp_provider] = lambda: None

    result = await request_otp(api, UGANDA)

    assert result["status"] == 503
    assert result["body"]["error"]["code"] == "OTP_CHANNEL_UNAVAILABLE"
    assert result["body"]["error"]["details"] == {"channel": "whatsapp"}
    assert api.sms.sent == []
    assert await latest_challenge(api) == []

    kenya = await request_otp(api, "0712345678")
    assert kenya["status"] == 201
    assert kenya["body"]["data"]["delivery_channel"] == "sms"


async def test_sms_failure_reports_the_sms_channel(api: IntegrationAPI) -> None:
    from app.integrations.sms.base import SMSDeliveryError

    api.sms.failure = SMSDeliveryError("provider_unavailable")

    result = await request_otp(api, "0712345678")

    assert result["status"] == 503
    assert result["body"]["error"]["details"] == {"channel": "sms", "retryable": True}
    assert "SMS" in result["body"]["error"]["message"]
    assert api.whatsapp.sent == []
