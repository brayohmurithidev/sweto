"""End-to-end phone authentication against PostgreSQL.

Covers the OTP lifecycle (send, resend, expiry, attempts, rate limits), SMS
delivery failures, and the session lifecycle the mobile app relies on
(refresh rotation, logout and logout-all).
"""

import logging

import pytest

from app.integrations.sms.base import SMSDeliveryError
from tests.integration.conftest import IntegrationAPI

MOBILE = "0712345678"
MOBILE_E164 = "+254712345678"


async def request_otp(api: IntegrationAPI, phone: str = MOBILE) -> dict:
    response = await api.client.post(
        "/api/v1/auth/request-otp", json={"phone_number": phone}
    )
    return {"status": response.status_code, "body": response.json()}


async def verify(api: IntegrationAPI, challenge_id: str, code: str) -> dict:
    response = await api.client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": challenge_id, "code": code, "platform": "flutter"},
    )
    return {"status": response.status_code, "body": response.json()}


async def sign_in(api: IntegrationAPI) -> dict:
    requested = await request_otp(api)
    assert requested["status"] == 201, requested
    verified = await verify(
        api, requested["body"]["data"]["challenge_id"], api.sms.last_code()
    )
    assert verified["status"] == 200, verified
    return verified["body"]["data"]["tokens"]


def error_code(result: dict) -> str:
    return result["body"]["error"]["code"]


# --- Sending -----------------------------------------------------------------


async def test_otp_is_sent_to_the_normalized_mobile_number(api: IntegrationAPI) -> None:
    result = await request_otp(api)

    assert result["status"] == 201
    assert result["body"]["data"]["phone_number"] == MOBILE_E164
    assert api.sms.sent[0][0] == MOBILE_E164
    assert len(api.sms.last_code()) == 6


async def test_otp_code_is_stored_hashed_not_in_plain_text(api: IntegrationAPI) -> None:
    await request_otp(api)

    rows = await api.sql("SELECT code_hash FROM otp_challenges")
    assert len(rows) == 1
    assert api.sms.last_code() not in str(rows[0][0])


@pytest.mark.parametrize("landline", ["0202222222", "+254412222222"])
async def test_landline_numbers_are_rejected_before_any_sms(
    api: IntegrationAPI, landline: str
) -> None:
    result = await request_otp(api, landline)

    assert result["status"] == 422
    assert error_code(result) == "INVALID_PHONE_NUMBER"
    assert "landline" in result["body"]["error"]["message"]
    assert api.sms.sent == []


async def test_resend_inside_the_cooldown_is_refused(api: IntegrationAPI) -> None:
    await request_otp(api)

    second = await request_otp(api)

    assert second["status"] == 429
    assert error_code(second) == "OTP_RESEND_COOLDOWN"
    assert second["body"]["error"]["details"]["retry_after_seconds"] > 0
    assert len(api.sms.sent) == 1


async def test_phone_rate_limit_applies_across_requests(api: IntegrationAPI) -> None:
    limit = api.settings.otp_request_phone_limit
    results = [await request_otp(api) for _ in range(limit + 1)]

    assert results[-1]["status"] == 429
    assert error_code(results[-1]) == "OTP_REQUEST_PHONE_RATE_LIMITED"


# --- Delivery failures ---------------------------------------------------------


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (SMSDeliveryError("provider_rejected", retryable=False), "provider_rejected"),
        (SMSDeliveryError("malformed_response"), "malformed_response"),
        (RuntimeError("socket closed"), "unexpected_RuntimeError"),
    ],
)
async def test_failed_delivery_returns_503_and_records_the_reason(
    api: IntegrationAPI, failure: Exception, reason: str
) -> None:
    api.sms.failure = failure

    result = await request_otp(api)

    assert result["status"] == 503
    assert error_code(result) == "OTP_DELIVERY_FAILED"
    rows = await api.sql(
        "SELECT status FROM otp_challenges ORDER BY created_at DESC LIMIT 1"
    )
    assert rows == [("expired",)]
    events = await api.sql(
        "SELECT metadata->>'reason' FROM auth_events "
        "WHERE event_type = 'otp_delivery_failed'"
    )
    assert events == [(reason,)]


async def test_provider_timeout_is_treated_as_a_delivery_failure(
    api: IntegrationAPI,
) -> None:
    api.sms.delay_seconds = api.settings.sms_send_timeout_seconds * 5

    result = await request_otp(api)

    assert result["status"] == 503
    events = await api.sql(
        "SELECT metadata->>'reason' FROM auth_events "
        "WHERE event_type = 'otp_delivery_failed'"
    )
    assert events == [("timeout",)]


async def test_user_can_retry_immediately_after_a_failed_delivery(
    api: IntegrationAPI,
) -> None:
    api.sms.failure = SMSDeliveryError("provider_unavailable")
    failed = await request_otp(api)
    assert failed["status"] == 503

    api.sms.failure = None
    retried = await request_otp(api)

    assert retried["status"] == 201
    verified = await verify(
        api, retried["body"]["data"]["challenge_id"], api.sms.last_code()
    )
    assert verified["status"] == 200


async def test_delivery_failure_never_logs_the_code(
    api: IntegrationAPI, caplog: pytest.LogCaptureFixture
) -> None:
    captured: list[str] = []

    class CodeCapturingFailure:
        async def send_otp(
            self, *, phone_number: str, otp_code: str, expires_in_seconds: int
        ) -> None:
            captured.append(otp_code)
            raise SMSDeliveryError("provider_rejected")

    from app.integrations.sms.dependencies import get_sms_provider
    from app.main import app

    app.dependency_overrides[get_sms_provider] = CodeCapturingFailure
    caplog.set_level(logging.DEBUG)

    result = await request_otp(api)

    assert result["status"] == 503
    assert captured
    assert captured[0] not in caplog.text
    assert "provider_rejected" in caplog.text


# --- Verification --------------------------------------------------------------


async def test_wrong_code_is_rejected_and_attempts_are_limited(
    api: IntegrationAPI,
) -> None:
    requested = await request_otp(api)
    challenge_id = requested["body"]["data"]["challenge_id"]
    wrong = "000000" if api.sms.last_code() != "000000" else "111111"

    results = [
        await verify(api, challenge_id, wrong)
        for _ in range(api.settings.otp_max_attempts)
    ]

    assert error_code(results[0]) == "INVALID_OTP"
    assert error_code(results[-1]) == "OTP_ATTEMPTS_EXCEEDED"
    after = await verify(api, challenge_id, api.sms.last_code())
    assert after["status"] != 200


async def test_expired_code_is_rejected(api: IntegrationAPI) -> None:
    requested = await request_otp(api)
    challenge_id = requested["body"]["data"]["challenge_id"]
    await api.sql("UPDATE otp_challenges SET expires_at = now() - interval '1 second'")

    result = await verify(api, challenge_id, api.sms.last_code())

    assert error_code(result) == "OTP_EXPIRED"


async def test_code_cannot_be_used_twice(api: IntegrationAPI) -> None:
    requested = await request_otp(api)
    challenge_id = requested["body"]["data"]["challenge_id"]
    code = api.sms.last_code()
    assert (await verify(api, challenge_id, code))["status"] == 200

    second = await verify(api, challenge_id, code)

    assert error_code(second) == "OTP_ALREADY_USED"


# --- Session lifecycle the app depends on --------------------------------------


async def refresh(api: IntegrationAPI, refresh_token: str) -> dict:
    response = await api.client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token, "platform": "flutter"},
    )
    return {"status": response.status_code, "body": response.json()}


async def test_refresh_rotates_and_detects_reuse(api: IntegrationAPI) -> None:
    tokens = await sign_in(api)

    rotated = await refresh(api, tokens["refresh_token"])
    assert rotated["status"] == 200
    new_refresh = rotated["body"]["data"]["tokens"]["refresh_token"]
    assert new_refresh != tokens["refresh_token"]

    reused = await refresh(api, tokens["refresh_token"])
    assert reused["status"] == 401


async def test_logout_revokes_the_session(api: IntegrationAPI) -> None:
    tokens = await sign_in(api)

    response = await api.client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 204

    after = await refresh(api, tokens["refresh_token"])
    assert after["status"] == 401
    assert error_code(after) == "REFRESH_SESSION_REVOKED"

    me = await api.client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 401


async def test_logout_everywhere_else_keeps_only_the_current_session(
    api: IntegrationAPI,
) -> None:
    other_device = await sign_in(api)
    await api.sql("UPDATE otp_challenges SET created_at = now() - interval '2 minutes'")
    this_device = await sign_in(api)

    response = await api.client.post(
        "/api/v1/auth/logout-all",
        json={"keep_current_session": True},
        headers={"Authorization": f"Bearer {this_device['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["revoked_sessions"] == 1
    assert (await refresh(api, other_device["refresh_token"]))["status"] == 401
    assert (await refresh(api, this_device["refresh_token"]))["status"] == 200


async def test_logout_all_can_include_the_current_session(api: IntegrationAPI) -> None:
    first = await sign_in(api)
    await api.sql("UPDATE otp_challenges SET created_at = now() - interval '2 minutes'")
    second = await sign_in(api)

    response = await api.client.post(
        "/api/v1/auth/logout-all",
        json={"keep_current_session": False},
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )

    assert response.status_code == 200
    for tokens in (first, second):
        assert (await refresh(api, tokens["refresh_token"]))["status"] == 401
