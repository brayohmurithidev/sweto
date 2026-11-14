"""Switching the SMS provider by configuration, through the real API.

The auth service, OTP logic and API contract are unchanged whichever adapter
is configured. HTTP goes to mocked transports; nothing reaches a provider.
"""

import logging
from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr

from app.integrations.sms.dependencies import get_sms_provider
from app.integrations.sms.registry import build_sms_provider
from app.main import app
from tests.integration.conftest import IntegrationAPI

KENYA = "0712345678"
KENYA_E164 = "+254712345678"
KEY = "provider-test-key-never-logged"

Handler = Callable[[httpx.Request], httpx.Response]


def use_provider(api: IntegrationAPI, handler: Handler, **settings: object) -> None:
    """Configure SMS_PROVIDER like a deployment would, with mocked HTTP."""

    configured = api.settings.model_copy(update=settings)
    provider = build_sms_provider(
        configured, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    app.dependency_overrides[get_sms_provider] = lambda: provider


ADVANTA: dict[str, object] = {
    "sms_provider": "advanta",
    "advanta_api_key": SecretStr(KEY),
    "advanta_partner_id": "1234",
    "advanta_shortcode": "SWETO",
}
AFRICASTALKING: dict[str, object] = {
    "sms_provider": "africastalking",
    "africastalking_environment": "live",
    "africastalking_username": "sweto",
    "africastalking_api_key": SecretStr(KEY),
    "africastalking_sender_id": "SWETO",
}


def advanta_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, json={"responses": [{"respose-code": 200, "messageid": 777}]}
    )


def africastalking_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        201,
        json={
            "SMSMessageData": {
                "Recipients": [{"statusCode": 101, "messageId": "ATXid_777"}]
            }
        },
    )


async def request_otp(api: IntegrationAPI, phone: str = KENYA) -> dict:
    response = await api.client.post(
        "/api/v1/auth/request-otp", json={"phone_number": phone}
    )
    return {"status": response.status_code, "body": response.json()}


async def challenge_row(api: IntegrationAPI) -> tuple[object, ...]:
    rows = await api.sql(
        "SELECT status, delivery_status, provider_message_id, delivery_channel "
        "FROM otp_challenges ORDER BY created_at DESC LIMIT 1"
    )
    return rows[0]


@pytest.mark.parametrize(
    ("settings", "handler", "message_id"),
    [
        (ADVANTA, advanta_ok, "777"),
        (AFRICASTALKING, africastalking_ok, "ATXid_777"),
    ],
    ids=["advanta", "africastalking"],
)
async def test_kenyan_codes_go_through_the_configured_provider(
    api: IntegrationAPI,
    settings: dict[str, object],
    handler: Handler,
    message_id: str,
) -> None:
    sent: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return handler(request)

    use_provider(api, recording, **settings)

    result = await request_otp(api)

    assert result["status"] == 201
    assert result["body"]["data"]["delivery_channel"] == "sms"
    assert len(sent) == 1
    # Accepted is recorded, never "delivered".
    assert await challenge_row(api) == ("pending", "accepted", message_id, "sms")
    assert api.whatsapp.sent == []


async def test_a_read_timeout_is_recorded_as_unknown_and_frees_a_resend(
    api: IntegrationAPI,
) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("no answer")

    use_provider(api, timeout, **AFRICASTALKING)

    result = await request_otp(api)

    assert result["status"] == 503
    assert result["body"]["error"]["code"] == "OTP_DELIVERY_FAILED"
    assert await challenge_row(api) == ("expired", "unknown", None, "sms")
    events = await api.sql(
        "SELECT metadata->>'reason', metadata->>'outcome_unknown' FROM auth_events "
        "WHERE event_type = 'otp_delivery_failed'"
    )
    assert events == [("timeout", "true")]

    # No cooldown and no fallback: the next request uses the same provider.
    use_provider(api, africastalking_ok, **AFRICASTALKING)
    assert (await request_otp(api))["status"] == 201


async def test_a_refused_connection_is_recorded_as_failed(
    api: IntegrationAPI,
) -> None:
    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    use_provider(api, refused, **ADVANTA)

    assert (await request_otp(api))["status"] == 503
    assert await challenge_row(api) == ("expired", "failed", None, "sms")


async def test_an_overall_timeout_is_recorded_as_unknown(api: IntegrationAPI) -> None:
    api.sms.delay_seconds = api.settings.sms_send_timeout_seconds * 5

    assert (await request_otp(api))["status"] == 503
    assert (await challenge_row(api))[:2] == ("expired", "unknown")


async def test_provider_rejection_is_normalized_and_not_retried_elsewhere(
    api: IntegrationAPI, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    calls: list[httpx.Request] = []

    def low_credit(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200,
            json={"responses": [{"respose-code": 1004, "response-description": "x"}]},
        )

    use_provider(api, low_credit, **ADVANTA)

    result = await request_otp(api)

    assert result["status"] == 503
    assert result["body"]["error"]["details"] == {"channel": "sms", "retryable": False}
    assert len(calls) == 1
    assert api.sms.sent == [] and api.whatsapp.sent == []
    events = await api.sql(
        "SELECT metadata->>'reason', metadata->>'provider_code' FROM auth_events "
        "WHERE event_type = 'otp_delivery_failed'"
    )
    assert events == [("insufficient_balance", "1004")]
    assert KEY not in caplog.text
    assert KENYA_E164 not in caplog.text
