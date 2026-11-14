"""Meta WhatsApp Cloud API provider, against mocked HTTP (no real Meta calls)."""

import json
import logging

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.integrations.whatsapp.base import WhatsAppDeliveryError
from app.integrations.whatsapp.meta import MetaWhatsAppConfig, MetaWhatsAppProvider

TOKEN = "test-access-token-not-real"
CODE = "482913"

CONFIG = MetaWhatsAppConfig(
    base_url="https://graph.facebook.com",
    api_version="v24.0",
    phone_number_id="1234567890",
    access_token=SecretStr(TOKEN),
    template_name="sweto_login_code",
    template_language="en",
    timeout_seconds=5,
)

_REQUIRED = {
    "database_url": "postgresql+asyncpg://sweto:pw@localhost:5432/sweto",
    "otp_hash_secret": "test-otp-secret-that-is-long-enough-for-secure-hmac",
    "jwt_secret_key": "test-jwt-secret-that-is-at-least-thirty-two-bytes",
}
_META = {
    "whatsapp_provider": "meta",
    "meta_graph_api_version": "v24.0",
    "meta_whatsapp_phone_number_id": "1234567890",
    "meta_whatsapp_access_token": TOKEN,
    "meta_whatsapp_otp_template_name": "sweto_login_code",
    "meta_whatsapp_otp_template_language": "en",
    "meta_app_secret": "test-app-secret",
    "meta_webhook_verify_token": "test-verify-token",
}


def provider(handler: httpx.MockTransport) -> MetaWhatsAppProvider:
    return MetaWhatsAppProvider(CONFIG, client=httpx.AsyncClient(transport=handler))


async def send(p: MetaWhatsAppProvider) -> str | None:
    return await p.send_otp(
        phone_number="+256701234567", otp_code=CODE, expires_in_seconds=300
    )


def meta_error(status: int, code: int | None) -> httpx.MockTransport:
    body = {"error": {"message": "(#x) +256701234567 failed", "type": "OAuthException"}}
    if code is not None:
        body["error"]["code"] = code  # type: ignore[index]
    return httpx.MockTransport(lambda request: httpx.Response(status, json=body))


async def test_sends_the_authentication_template_to_the_phone_number_id() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "messaging_product": "whatsapp",
                "contacts": [{"input": "+256701234567", "wa_id": "256701234567"}],
                "messages": [{"id": "wamid.ABC123"}],
            },
        )

    message_id = await send(provider(httpx.MockTransport(handler)))

    assert message_id == "wamid.ABC123"
    request = captured[0]
    assert request.method == "POST"
    assert str(request.url) == "https://graph.facebook.com/v24.0/1234567890/messages"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.headers["Content-Type"] == "application/json"
    assert json.loads(request.content) == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        # E.164 with "+": without it Meta prepends the sender's country code.
        "to": "+256701234567",
        "type": "template",
        "template": {
            "name": "sweto_login_code",
            "language": {"code": "en"},
            "components": [
                {"type": "body", "parameters": [{"type": "text", "text": CODE}]},
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": CODE}],
                },
            ],
        },
    }


@pytest.mark.parametrize(
    ("status", "code", "reason", "retryable"),
    [
        (401, 190, "unauthorized", False),  # expired or invalid token
        (403, 10, "unauthorized", False),  # permission removed
        (400, 131026, "recipient_undeliverable", False),
        (400, 132001, "template_rejected", False),  # missing or unapproved
        (400, 132012, "template_rejected", False),
        (400, 132015, "template_rejected", False),  # paused
        (429, 130429, "rate_limited", True),
        (400, 131056, "rate_limited", True),  # pair rate limit
        (400, 80007, "rate_limited", True),
        (400, 100, "invalid_request", False),
        (500, None, "provider_unavailable", True),
        (503, 131016, "provider_unavailable", True),
        (400, 999999, "provider_rejected", False),
    ],
)
async def test_meta_errors_map_to_stable_reasons(
    status: int, code: int | None, reason: str, retryable: bool
) -> None:
    with pytest.raises(WhatsAppDeliveryError) as raised:
        await send(provider(meta_error(status, code)))

    error = raised.value
    assert error.reason == reason
    assert error.retryable is retryable
    assert error.provider_code == (str(code) if code is not None else f"http_{status}")
    # Meta's message can contain the number; it is never copied.
    assert "256701234567" not in str(error)


async def test_timeout_is_a_retryable_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(WhatsAppDeliveryError) as raised:
        await send(provider(httpx.MockTransport(handler)))
    assert (raised.value.reason, raised.value.retryable) == ("timeout", True)


async def test_network_failure_is_a_retryable_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(WhatsAppDeliveryError) as raised:
        await send(provider(httpx.MockTransport(handler)))
    assert raised.value.reason == "provider_unreachable"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>not json</html>"),
        httpx.Response(200, json={"messages": []}),
        httpx.Response(200, json={"messages": [{"id": ""}]}),
        httpx.Response(200, json=["unexpected"]),
    ],
)
async def test_malformed_success_response_is_a_failure(
    response: httpx.Response,
) -> None:
    with pytest.raises(WhatsAppDeliveryError) as raised:
        await send(provider(httpx.MockTransport(lambda request: response)))
    assert raised.value.reason == "malformed_response"


async def test_error_body_that_is_not_json_still_maps(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(502, text="Bad gateway")
    )
    with pytest.raises(WhatsAppDeliveryError) as raised:
        await send(provider(transport))
    assert (raised.value.reason, raised.value.provider_code) == (
        "provider_unavailable",
        "http_502",
    )


async def test_nothing_secret_reaches_logs_or_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    with pytest.raises(WhatsAppDeliveryError) as raised:
        await send(provider(meta_error(401, 190)))

    for text in (caplog.text, str(raised.value), repr(raised.value), repr(CONFIG)):
        assert TOKEN not in text
        assert CODE not in text


def test_meta_provider_needs_every_setting() -> None:
    with pytest.raises(ValidationError) as raised:
        Settings(**_REQUIRED, whatsapp_provider="meta")
    message = str(raised.value)
    for name in (
        "META_GRAPH_API_VERSION",
        "META_WHATSAPP_PHONE_NUMBER_ID",
        "META_WHATSAPP_ACCESS_TOKEN",
        "META_WHATSAPP_OTP_TEMPLATE_NAME",
        "META_WHATSAPP_OTP_TEMPLATE_LANGUAGE",
        "META_APP_SECRET",
        "META_WEBHOOK_VERIFY_TOKEN",
    ):
        assert name in message


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("meta_graph_api_version", "24", "v24.0"),
        ("meta_whatsapp_phone_number_id", "abc", "numeric"),
        ("meta_whatsapp_otp_template_name", "Login Code", "lowercase"),
        ("meta_graph_api_base_url", "http://graph.facebook.com", "https"),
    ],
)
def test_meta_settings_are_checked(field: str, value: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(**_REQUIRED, **{**_META, field: value})


def test_complete_meta_settings_build_the_provider_config() -> None:
    settings = Settings(**_REQUIRED, **_META)
    config = MetaWhatsAppConfig.from_settings(settings)

    assert config.messages_url == (
        "https://graph.facebook.com/v24.0/1234567890/messages"
    )
    assert TOKEN not in repr(settings)
    assert "test-app-secret" not in repr(settings)
