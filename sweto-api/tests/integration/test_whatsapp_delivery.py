"""WhatsApp delivery reports end to end, against PostgreSQL.

The WhatsApp provider is an in-memory double (no Meta calls); settings are
switched to WHATSAPP_PROVIDER=meta so the webhook is enabled.
"""

import hashlib
import hmac
import json
import logging

import pytest
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.integrations.whatsapp.base import WhatsAppDeliveryError
from app.integrations.whatsapp.dependencies import get_whatsapp_provider
from app.main import app
from tests.integration.conftest import IntegrationAPI

UGANDA = "+256701234567"
PHONE_NUMBER_ID = "1234567890"
APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"
WEBHOOK = "/api/v1/webhooks/whatsapp"


@pytest.fixture(autouse=True)
def meta_settings(api: IntegrationAPI) -> None:
    settings = api.settings.model_copy(
        update={
            "whatsapp_provider": "meta",
            "meta_graph_api_version": "v24.0",
            "meta_whatsapp_phone_number_id": PHONE_NUMBER_ID,
            "meta_whatsapp_access_token": SecretStr("test-token"),
            "meta_whatsapp_otp_template_name": "sweto_login_code",
            "meta_whatsapp_otp_template_language": "en",
            "meta_app_secret": SecretStr(APP_SECRET),
            "meta_webhook_verify_token": SecretStr(VERIFY_TOKEN),
        }
    )
    app.dependency_overrides[get_settings] = lambda: settings


async def request_code(api: IntegrationAPI, phone: str = UGANDA) -> dict:
    response = await api.client.post(
        "/api/v1/auth/request-otp", json={"phone_number": phone}
    )
    assert response.status_code == 201, response.json()
    return response.json()["data"]


async def post_statuses(
    api: IntegrationAPI, *statuses: dict, secret: str = APP_SECRET
) -> int:
    body = json.dumps(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA_ID",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": PHONE_NUMBER_ID},
                                "statuses": list(statuses),
                            },
                        }
                    ],
                }
            ],
        }
    ).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    response = await api.client.post(
        WEBHOOK,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={signature}",
        },
    )
    return response.status_code


async def challenge_state(api: IntegrationAPI, challenge_id: str) -> tuple:
    rows = await api.sql(
        "SELECT status, delivery_status, delivery_error_code FROM otp_challenges "
        "WHERE id = :id",
        id=challenge_id,
    )
    return rows[0]


async def delivery(api: IntegrationAPI, challenge_id: str) -> str:
    response = await api.client.get(
        f"/api/v1/auth/otp-challenges/{challenge_id}/delivery"
    )
    assert response.status_code == 200
    return response.json()["data"]["delivery_status"]


# --- Sending -----------------------------------------------------------------


async def test_accepted_send_is_recorded_but_not_as_delivered(
    api: IntegrationAPI,
) -> None:
    data = await request_code(api)

    assert data["delivery_channel"] == "whatsapp"
    assert await challenge_state(api, data["challenge_id"]) == (
        "pending",
        "accepted",
        None,
    )
    rows = await api.sql(
        "SELECT provider_message_id FROM otp_challenges WHERE id = :id",
        id=data["challenge_id"],
    )
    assert rows == [(api.whatsapp.last_message_id(),)]
    assert await delivery(api, data["challenge_id"]) == "accepted"


async def test_kenya_still_uses_sms_and_whatsapp_numbers_never_fall_back(
    api: IntegrationAPI,
) -> None:
    kenya = await request_code(api, "0712345678")
    assert kenya["delivery_channel"] == "sms"
    assert api.whatsapp.sent == []

    api.whatsapp.failure = WhatsAppDeliveryError(
        "template_rejected", retryable=False, provider_code="132001"
    )
    response = await api.client.post(
        "/api/v1/auth/request-otp", json={"phone_number": UGANDA}
    )
    assert response.status_code == 503
    assert [phone for phone, _ in api.sms.sent] == ["+254712345678"]
    events = await api.sql(
        "SELECT metadata->>'reason', metadata->>'provider_code' FROM auth_events "
        "WHERE event_type = 'otp_delivery_failed'"
    )
    assert events == [("template_rejected", "132001")]


async def test_disabled_whatsapp_makes_no_provider_request(api: IntegrationAPI) -> None:
    app.dependency_overrides[get_whatsapp_provider] = lambda: None

    response = await api.client.post(
        "/api/v1/auth/request-otp", json={"phone_number": UGANDA}
    )

    assert response.status_code == 503
    assert api.whatsapp.sent == [] and api.sms.sent == []


# --- Countries offered to the app ----------------------------------------------


async def test_phone_countries_list_only_channels_that_are_on(
    api: IntegrationAPI,
) -> None:
    response = await api.client.get("/api/v1/auth/phone-countries")
    countries = response.json()["data"]["countries"]
    assert countries[0] == {
        "region": "KE",
        "dial_code": "254",
        "delivery_channel": "sms",
    }
    assert {c["region"] for c in countries} == {
        "KE",
        "UG",
        "TZ",
        "RW",
        "BI",
        "SS",
        "CD",
        "SO",
    }
    assert {c["delivery_channel"] for c in countries[1:]} == {"whatsapp"}

    app.dependency_overrides[get_whatsapp_provider] = lambda: None
    response = await api.client.get("/api/v1/auth/phone-countries")
    assert response.json()["data"]["countries"] == [
        {"region": "KE", "dial_code": "254", "delivery_channel": "sms"}
    ]


# --- Webhook verification ------------------------------------------------------


async def test_webhook_verification_echoes_the_challenge(api: IntegrationAPI) -> None:
    response = await api.client.get(
        WEBHOOK,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "1158201444",
        },
    )
    assert response.status_code == 200
    assert response.text == "1158201444"


@pytest.mark.parametrize(
    "params",
    [
        {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"},
        {
            "hub.mode": "unsubscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "1",
        },
        {"hub.mode": "subscribe", "hub.challenge": "1"},
        {},
    ],
)
async def test_webhook_verification_rejects_bad_requests(
    api: IntegrationAPI, params: dict
) -> None:
    response = await api.client.get(WEBHOOK, params=params)
    assert response.status_code == 403


async def test_webhook_is_off_unless_meta_is_the_provider(api: IntegrationAPI) -> None:
    app.dependency_overrides[get_settings] = lambda: api.settings
    verify = await api.client.get(
        WEBHOOK,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "1",
        },
    )
    notify = await api.client.post(WEBHOOK, content=b"{}")
    assert (verify.status_code, notify.status_code) == (404, 404)


# --- Status reports -------------------------------------------------------------


async def test_unsigned_or_badly_signed_reports_change_nothing(
    api: IntegrationAPI,
) -> None:
    data = await request_code(api)
    failed = {"id": api.whatsapp.last_message_id(), "status": "failed"}

    assert await post_statuses(api, failed, secret="wrong-secret") == 401
    unsigned = await api.client.post(WEBHOOK, json={"entry": []})
    assert unsigned.status_code == 401
    assert await challenge_state(api, data["challenge_id"]) == (
        "pending",
        "accepted",
        None,
    )


async def test_signed_but_invalid_json_is_rejected(api: IntegrationAPI) -> None:
    body = b"not json"
    signature = hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    response = await api.client.post(
        WEBHOOK, content=body, headers={"X-Hub-Signature-256": f"sha256={signature}"}
    )
    assert response.status_code == 400


async def test_statuses_only_move_forward_and_duplicates_are_harmless(
    api: IntegrationAPI,
) -> None:
    data = await request_code(api)
    message_id = api.whatsapp.last_message_id()

    for status, expected in [
        ("sent", "sent"),
        ("delivered", "delivered"),
        ("delivered", "delivered"),  # duplicate
        ("sent", "delivered"),  # late, older status
        ("read", "read"),
        ("failed", "read"),  # failure after delivery is ignored
    ]:
        assert await post_statuses(api, {"id": message_id, "status": status}) == 200
        assert await delivery(api, data["challenge_id"]) == expected

    # Delivery reports never touch whether the code is usable.
    assert (await challenge_state(api, data["challenge_id"]))[0] == "pending"


async def test_failed_delivery_retires_the_code_and_allows_a_new_one_at_once(
    api: IntegrationAPI,
) -> None:
    data = await request_code(api)
    old_code = api.whatsapp.last_code()
    failed = {
        "id": api.whatsapp.last_message_id(),
        "status": "failed",
        "errors": [{"code": 131026, "title": "Message undeliverable"}],
    }

    assert await post_statuses(api, failed) == 200
    assert await post_statuses(api, failed) == 200  # Meta retry: no change

    assert await challenge_state(api, data["challenge_id"]) == (
        "expired",
        "failed",
        "131026",
    )
    assert await delivery(api, data["challenge_id"]) == "failed"
    events = await api.sql(
        "SELECT metadata->>'source', metadata->>'provider_code' FROM auth_events "
        "WHERE event_type = 'otp_delivery_failed'"
    )
    assert events == [("webhook", "131026")]

    # No resend cooldown for a code that never arrived.
    again = await request_code(api)
    assert again["challenge_id"] != data["challenge_id"]

    # The undelivered code can't be used.
    verify = await api.client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": data["challenge_id"], "code": old_code},
    )
    assert verify.status_code != 200


async def test_failure_report_after_sign_in_leaves_the_session_alone(
    api: IntegrationAPI,
) -> None:
    data = await request_code(api)
    verified = await api.client.post(
        "/api/v1/auth/verify-otp",
        json={
            "challenge_id": data["challenge_id"],
            "code": api.whatsapp.last_code(),
            "platform": "flutter",
        },
    )
    assert verified.status_code == 200

    failed = {"id": api.whatsapp.last_message_id(), "status": "failed"}
    assert await post_statuses(api, failed) == 200

    assert (await challenge_state(api, data["challenge_id"]))[0] == "verified"
    events = await api.sql(
        "SELECT metadata->>'challenge_retired' FROM auth_events "
        "WHERE event_type = 'otp_delivery_failed'"
    )
    assert events == [("false",)]
    me = await api.client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": "Bearer "
            + verified.json()["data"]["tokens"]["access_token"]
        },
    )
    assert me.status_code == 200


async def test_reports_for_unknown_messages_or_other_numbers_are_ignored(
    api: IntegrationAPI,
) -> None:
    data = await request_code(api)

    assert await post_statuses(api, {"id": "wamid.unknown", "status": "failed"}) == 200
    assert await challenge_state(api, data["challenge_id"]) == (
        "pending",
        "accepted",
        None,
    )


async def test_webhook_and_sending_log_no_secrets_or_codes(
    api: IntegrationAPI, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    await request_code(api)
    code = api.whatsapp.last_code()
    await post_statuses(api, {"id": api.whatsapp.last_message_id(), "status": "failed"})
    await post_statuses(api, {"id": "x", "status": "sent"}, secret="wrong")

    for secret in (code, APP_SECRET, VERIFY_TOKEN, "test-token", "256701234567"):
        assert secret not in caplog.text


async def test_delivery_status_for_an_unknown_challenge_is_404(
    api: IntegrationAPI,
) -> None:
    response = await api.client.get(
        "/api/v1/auth/otp-challenges/00000000-0000-0000-0000-000000000000/delivery"
    )
    assert response.status_code == 404


# --- One usable code per number ------------------------------------------------


async def test_database_allows_only_one_pending_code_per_number(
    api: IntegrationAPI,
) -> None:
    await request_code(api)

    with pytest.raises(IntegrityError):
        await api.sql(
            "INSERT INTO otp_challenges (id, phone_number, purpose, status, "
            "code_hash, expires_at, max_attempts, attempt_count) "
            "VALUES (gen_random_uuid(), :phone, 'login', 'pending', 'x', "
            "now() + interval '5 minutes', 5, 0)",
            phone=UGANDA,
        )
