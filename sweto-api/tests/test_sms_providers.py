"""SMS provider adapters, registry and configuration.

Every HTTP call goes to an httpx MockTransport; nothing reaches Advanta or
Africa's Talking.
"""

import inspect
import json
import logging
from collections.abc import Callable
from urllib.parse import parse_qs

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import (
    ConfigurationError,
    Settings,
    get_settings,
    sanitized_settings_error,
)
from app.integrations.http_errors import transport_error
from app.integrations.sms.advanta import AdvantaConfig, AdvantaSMSProvider
from app.integrations.sms.africastalking import (
    AfricasTalkingConfig,
    AfricasTalkingSMSProvider,
)
from app.integrations.sms.base import SMSDeliveryError, SMSProvider
from app.integrations.sms.console import ConsoleSMSProvider
from app.integrations.sms.registry import SMS_PROVIDERS, build_sms_provider
from app.integrations.whatsapp.base import WhatsAppDeliveryError

_REQUIRED = {
    "database_url": "postgresql+asyncpg://sweto:pw@localhost:5432/sweto",
    "otp_hash_secret": "test-otp-secret-that-is-long-enough-for-secure-hmac",
    "jwt_secret_key": "test-jwt-secret-that-is-at-least-thirty-two-bytes",
}
ADVANTA_KEY = "advanta-test-key-should-never-appear"
AT_KEY = "atsk-test-key-should-never-appear"
CODE = "482913"
PHONE = "+254712345678"

ADVANTA = AdvantaConfig(
    base_url="https://quicksms.advantasms.com",
    api_key=SecretStr(ADVANTA_KEY),
    partner_id="1234",
    shortcode="SWETO",
    timeout_seconds=5,
)
AT_LIVE = AfricasTalkingConfig(
    base_url="https://api.africastalking.com",
    username="sweto",
    api_key=SecretStr(AT_KEY),
    sender_id="SWETO",
    timeout_seconds=5,
)

Handler = Callable[[httpx.Request], httpx.Response]


def advanta(handler: Handler) -> AdvantaSMSProvider:
    return AdvantaSMSProvider(
        ADVANTA, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


def africastalking(
    handler: Handler, config: AfricasTalkingConfig = AT_LIVE
) -> AfricasTalkingSMSProvider:
    return AfricasTalkingSMSProvider(
        config, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


async def send(provider: SMSProvider) -> str | None:
    return await provider.send_otp(
        phone_number=PHONE, otp_code=CODE, expires_in_seconds=300
    )


def reply(status: int, body: object) -> Handler:
    return lambda request: httpx.Response(status, json=body)


def raises(exc: Exception) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    return handler


def at_reply(status_code: int, message_id: str = "ATXid_abc") -> Handler:
    return reply(
        201,
        {
            "SMSMessageData": {
                "Message": "Sent to 1/1 Total Cost: KES 0.8000",
                "Recipients": [
                    {
                        "statusCode": status_code,
                        "number": PHONE,
                        "status": "Success",
                        "cost": "KES 0.8000",
                        "messageId": message_id,
                    }
                ],
            }
        },
    )


# --- One contract -----------------------------------------------------------


@pytest.mark.parametrize(
    "adapter", [ConsoleSMSProvider, AdvantaSMSProvider, AfricasTalkingSMSProvider]
)
def test_every_sms_adapter_implements_the_same_contract(adapter: type) -> None:
    expected = inspect.signature(SMSProvider.send_otp)
    actual = inspect.signature(adapter.send_otp)
    assert list(actual.parameters) == list(expected.parameters)
    assert actual.return_annotation == expected.return_annotation
    assert inspect.iscoroutinefunction(adapter.send_otp)


def test_registry_lists_exactly_the_supported_providers() -> None:
    assert set(SMS_PROVIDERS) == {"console", "advanta", "africastalking"}


# --- Selection by configuration ---------------------------------------------


def test_console_is_selected_by_default() -> None:
    assert isinstance(build_sms_provider(Settings(**_REQUIRED)), ConsoleSMSProvider)


def test_advanta_is_selected_by_configuration() -> None:
    settings = Settings(
        **_REQUIRED,
        sms_provider="advanta",
        advanta_api_key=ADVANTA_KEY,
        advanta_partner_id="1234",
        advanta_shortcode="SWETO",
    )
    assert isinstance(build_sms_provider(settings), AdvantaSMSProvider)


def test_africastalking_is_selected_by_configuration() -> None:
    settings = Settings(
        **_REQUIRED,
        sms_provider="africastalking",
        africastalking_environment="live",
        africastalking_username="sweto",
        africastalking_api_key=AT_KEY,
    )
    provider = build_sms_provider(settings)
    assert isinstance(provider, AfricasTalkingSMSProvider)


def test_unknown_provider_fails_without_falling_back() -> None:
    settings = Settings.model_construct(sms_provider="twilio")
    with pytest.raises(ConfigurationError, match="Unknown SMS_PROVIDER 'twilio'"):
        build_sms_provider(settings)
    with pytest.raises(ValidationError):
        Settings(**_REQUIRED, sms_provider="twilio")


@pytest.mark.parametrize(
    ("overrides", "names"),
    [
        (
            {"sms_provider": "advanta"},
            "ADVANTA_API_KEY, ADVANTA_PARTNER_ID, ADVANTA_SHORTCODE",
        ),
        (
            {"sms_provider": "advanta", "advanta_api_key": ADVANTA_KEY},
            "ADVANTA_PARTNER_ID, ADVANTA_SHORTCODE",
        ),
        (
            {"sms_provider": "africastalking"},
            "AFRICASTALKING_ENVIRONMENT, AFRICASTALKING_USERNAME, "
            "AFRICASTALKING_API_KEY",
        ),
    ],
)
def test_missing_provider_settings_fail_at_startup(
    overrides: dict[str, str], names: str
) -> None:
    with pytest.raises(ValidationError, match=f"needs these settings: {names}"):
        Settings(**_REQUIRED, **overrides)


def test_africastalking_sandbox_needs_the_sandbox_username() -> None:
    with pytest.raises(ValidationError, match="must be 'sandbox'"):
        Settings(
            **_REQUIRED,
            sms_provider="africastalking",
            africastalking_environment="sandbox",
            africastalking_username="sweto",
            africastalking_api_key=AT_KEY,
        )


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_africastalking_sandbox_is_refused_where_real_users_sign_in(
    environment: str,
) -> None:
    with pytest.raises(ValidationError, match="doesn't deliver real SMS"):
        Settings(
            **_REQUIRED,
            app_environment=environment,
            sms_provider="africastalking",
            africastalking_environment="sandbox",
            africastalking_username="sandbox",
            africastalking_api_key=AT_KEY,
        )


def test_configuration_errors_never_show_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValidationError) as raised:
        Settings(**_REQUIRED, sms_provider="advanta", advanta_api_key=ADVANTA_KEY)
    # Pydantic's own message repeats the input; ours must not.
    sanitized = str(sanitized_settings_error(raised.value))
    assert "ADVANTA_PARTNER_ID" in sanitized
    assert ADVANTA_KEY not in sanitized
    assert _REQUIRED["jwt_secret_key"] not in sanitized

    for name, value in {
        **{key.upper(): val for key, val in _REQUIRED.items()},
        "SMS_PROVIDER": "advanta",
        "ADVANTA_API_KEY": ADVANTA_KEY,
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("ADVANTA_PARTNER_ID", raising=False)
    with pytest.raises(ConfigurationError) as startup:
        get_settings.__wrapped__()
    assert "ADVANTA_PARTNER_ID" in str(startup.value)
    assert ADVANTA_KEY not in str(startup.value)
    assert startup.value.__cause__ is None
    assert startup.value.__suppress_context__


# --- Advanta ----------------------------------------------------------------


async def test_advanta_sends_its_documented_request() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "responses": [
                    {
                        "respose-code": 200,
                        "response-description": "Success",
                        "mobile": 254712345678,
                        "messageid": 8290842,
                        "networkid": "1",
                    }
                ]
            },
        )

    assert await send(advanta(handler)) == "8290842"
    request = captured[0]
    assert request.method == "POST"
    assert str(request.url) == "https://quicksms.advantasms.com/api/services/sendsms/"
    body = json.loads(request.content)
    assert set(body) == {"apikey", "partnerID", "message", "shortcode", "mobile"}
    assert body["apikey"] == ADVANTA_KEY
    assert body["partnerID"] == "1234"
    assert body["shortcode"] == "SWETO"
    assert body["mobile"] == "254712345678"
    assert body["message"].startswith(f"{CODE} is your SWETO verification code.")


async def test_advanta_accepts_the_correctly_spelled_code_key() -> None:
    handler = reply(200, {"responses": [{"response-code": 200, "messageid": "abc"}]})
    assert await send(advanta(handler)) == "abc"


@pytest.mark.parametrize(
    ("code", "reason", "retryable"),
    [
        (1001, "sender_id_rejected", False),
        (1002, "invalid_recipient", False),
        (1003, "invalid_recipient", False),
        (1004, "insufficient_balance", False),
        (1005, "provider_unavailable", True),
        (1006, "unauthorized", False),
        (4090, "provider_unavailable", True),
        (4092, "unauthorized", False),
        (9999, "provider_rejected", False),
    ],
)
async def test_advanta_result_codes_are_normalized(
    code: int, reason: str, retryable: bool
) -> None:
    handler = reply(
        200,
        {"responses": [{"respose-code": code, "response-description": PHONE}]},
    )
    with pytest.raises(SMSDeliveryError) as raised:
        await send(advanta(handler))
    assert (raised.value.reason, raised.value.retryable) == (reason, retryable)
    assert raised.value.provider_code == str(code)
    assert raised.value.outcome_unknown is False


@pytest.mark.parametrize(
    ("status", "reason", "retryable"),
    [
        (401, "unauthorized", False),
        (403, "unauthorized", False),
        (400, "provider_rejected", False),
        (502, "provider_unavailable", True),
    ],
)
async def test_advanta_http_errors_are_normalized(
    status: int, reason: str, retryable: bool
) -> None:
    with pytest.raises(SMSDeliveryError) as raised:
        await send(advanta(reply(status, {"error": PHONE})))
    assert (raised.value.reason, raised.value.retryable) == (reason, retryable)


async def test_advanta_unreadable_success_is_an_unknown_outcome() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>ok</html>")

    with pytest.raises(SMSDeliveryError) as raised:
        await send(advanta(handler))
    assert raised.value.reason == "malformed_response"
    assert raised.value.outcome_unknown is True


# --- Africa's Talking -------------------------------------------------------


async def test_africastalking_sends_its_documented_request() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return at_reply(101, "ATXid_123")(request)

    assert await send(africastalking(handler)) == "ATXid_123"
    request = captured[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.africastalking.com/version1/messaging"
    assert request.headers["apiKey"] == AT_KEY
    assert request.headers["Accept"] == "application/json"
    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    form = {
        key: values[0] for key, values in parse_qs(request.content.decode()).items()
    }
    assert form["username"] == "sweto"
    assert form["to"] == PHONE  # with the +, as the SDKs require
    assert form["from"] == "SWETO"
    assert form["bulkSMSMode"] == "1"
    assert form["message"].startswith(f"{CODE} is your SWETO verification code.")


async def test_africastalking_sandbox_without_sender_id() -> None:
    captured: list[httpx.Request] = []
    sandbox = AfricasTalkingConfig(
        base_url="https://api.sandbox.africastalking.com",
        username="sandbox",
        api_key=SecretStr(AT_KEY),
        sender_id=None,
        timeout_seconds=5,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return at_reply(100)(request)

    await send(africastalking(handler, sandbox))
    assert captured[0].url.host == "api.sandbox.africastalking.com"
    assert "from" not in parse_qs(captured[0].content.decode())


@pytest.mark.parametrize("status_code", [100, 101, 102])
async def test_africastalking_accepted_statuses(status_code: int) -> None:
    assert await send(africastalking(at_reply(status_code))) == "ATXid_abc"


@pytest.mark.parametrize(
    ("status_code", "reason", "retryable"),
    [
        (401, "provider_rejected", False),
        (402, "sender_id_rejected", False),
        (403, "invalid_recipient", False),
        (404, "invalid_recipient", False),
        (405, "insufficient_balance", False),
        (406, "recipient_blocked", False),
        (407, "provider_rejected", False),
        (500, "provider_unavailable", True),
        (501, "provider_unavailable", True),
        (502, "provider_rejected", False),
        (999, "provider_rejected", False),
    ],
)
async def test_africastalking_recipient_statuses_are_normalized(
    status_code: int, reason: str, retryable: bool
) -> None:
    with pytest.raises(SMSDeliveryError) as raised:
        await send(africastalking(at_reply(status_code)))
    assert (raised.value.reason, raised.value.retryable) == (reason, retryable)
    assert raised.value.provider_code == str(status_code)


@pytest.mark.parametrize(
    ("status", "reason", "retryable"),
    [
        (401, "unauthorized", False),
        (429, "rate_limited", True),
        (400, "provider_rejected", False),
        (503, "provider_unavailable", True),
    ],
)
async def test_africastalking_http_errors_are_normalized(
    status: int, reason: str, retryable: bool
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="The supplied key")

    with pytest.raises(SMSDeliveryError) as raised:
        await send(africastalking(handler))
    assert (raised.value.reason, raised.value.retryable) == (reason, retryable)


@pytest.mark.parametrize(
    "body", [{}, {"SMSMessageData": {"Recipients": []}}, {"SMSMessageData": 1}]
)
async def test_africastalking_unreadable_success_is_an_unknown_outcome(
    body: object,
) -> None:
    with pytest.raises(SMSDeliveryError) as raised:
        await send(africastalking(reply(201, body)))
    assert raised.value.reason == "malformed_response"
    assert raised.value.outcome_unknown is True


# --- Timeouts and ambiguous outcomes ----------------------------------------


@pytest.mark.parametrize("build", [advanta, africastalking])
@pytest.mark.parametrize(
    ("exc", "reason", "unknown"),
    [
        (httpx.ConnectError("refused"), "provider_unreachable", False),
        (httpx.ConnectTimeout("slow connect"), "provider_unreachable", False),
        (httpx.ReadTimeout("no answer"), "timeout", True),
        (httpx.RemoteProtocolError("dropped"), "provider_unreachable", True),
    ],
)
async def test_transport_failures_say_whether_the_message_may_have_gone(
    build: Callable[[Handler], SMSProvider],
    exc: Exception,
    reason: str,
    unknown: bool,
) -> None:
    with pytest.raises(SMSDeliveryError) as raised:
        await send(build(raises(exc)))
    assert raised.value.reason == reason
    assert raised.value.outcome_unknown is unknown


def test_whatsapp_uses_the_same_transport_classification() -> None:
    read = transport_error(httpx.ReadTimeout("x"), WhatsAppDeliveryError)
    connect = transport_error(httpx.ConnectError("x"), WhatsAppDeliveryError)
    assert isinstance(read, WhatsAppDeliveryError) and read.outcome_unknown
    assert not connect.outcome_unknown


# --- No secrets or codes in logs or errors ----------------------------------


@pytest.mark.parametrize(
    "provider",
    [
        lambda: advanta(reply(200, {"responses": [{"respose-code": 1006}]})),
        lambda: advanta(reply(500, {"echo": ADVANTA_KEY})),
        lambda: africastalking(at_reply(405)),
        lambda: africastalking(raises(httpx.ReadTimeout(AT_KEY))),
    ],
)
async def test_failures_never_log_keys_codes_or_numbers(
    provider: Callable[[], SMSProvider], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with pytest.raises(SMSDeliveryError) as raised:
        await send(provider())
    text = caplog.text + str(raised.value) + repr(raised.value)
    for secret in (ADVANTA_KEY, AT_KEY, CODE, PHONE, PHONE[1:]):
        assert secret not in text
