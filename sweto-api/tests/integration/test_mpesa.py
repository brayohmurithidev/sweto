"""M-Pesa renewals: STK Push, callback, reconcile (MVP build order, PR 6)."""

from typing import Any

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.integrations.mpesa.base import MpesaError, StkPushAccepted, StkResult
from app.integrations.mpesa.dependencies import get_mpesa_gateway
from app.jobs.mpesa_reconcile import reconcile_pending
from app.main import app
from tests.integration.conftest import IntegrationAPI, PinnedClock
from tests.integration.test_gym_members import gym_with_plans, pay_cash
from tests.integration.test_gym_owner_journey import FakeStorage, Owner, sign_in_owner

pytestmark = pytest.mark.usefixtures("pinned_clock")
TOKEN = "callback-token-for-tests-0123456789"


class FakeGateway:
    def __init__(self) -> None:
        self.pushes: list[dict[str, Any]] = []
        self.push_error: MpesaError | None = None
        self.query_results: dict[str, StkResult | None] = {}
        self.queried_accounts: list[Any] = []

    async def stk_push(self, **kwargs: Any) -> StkPushAccepted:
        if self.push_error:
            raise self.push_error
        self.pushes.append(kwargs)
        return StkPushAccepted(
            merchant_request_id=f"MR-{len(self.pushes)}",
            checkout_request_id=f"ws_CO_{len(self.pushes)}",
        )

    async def stk_query(
        self, *, account: Any, checkout_request_id: str
    ) -> StkResult | None:
        self.queried_accounts.append(account)
        return self.query_results.get(checkout_request_id)


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


@pytest.fixture
def gateway(api: IntegrationAPI) -> FakeGateway:
    fake = FakeGateway()
    app.dependency_overrides[get_mpesa_gateway] = lambda: fake
    api.settings.mpesa_callback_token = SecretStr(TOKEN)
    # Gyms without their own till use the default account outside production.
    api.settings.mpesa_mode = "simulated"
    return fake


async def member_with_plan(
    api: IntegrationAPI, storage: FakeStorage, *, consent: bool = True
) -> tuple[Owner, str, str, dict[str, str]]:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    response = await owner.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={
            "full_name": "Achieng Otieno",
            "phone_number": "0711000001",
            "sms_consent": consent,
        },
    )
    return owner, gym_id, response.json()["data"]["id"], plans


async def request(
    owner: Owner, gym_id: str, member_id: str, plan_id: str, **extra: Any
) -> Any:
    return await owner.call(
        "POST",
        f"/gyms/{gym_id}/members/{member_id}/payments/mpesa",
        json={"plan_id": plan_id, **extra},
    )


def callback_body(checkout: str, code: int = 0, amount: float = 5000) -> dict[str, Any]:
    callback: dict[str, Any] = {
        "MerchantRequestID": "MR-1",
        "CheckoutRequestID": checkout,
        "ResultCode": code,
        "ResultDesc": "The service request is processed successfully."
        if code == 0
        else "Request cancelled by user",
    }
    if code == 0:
        callback["CallbackMetadata"] = {
            "Item": [
                {"Name": "Amount", "Value": amount},
                {"Name": "MpesaReceiptNumber", "Value": "TKE1ABC2DE"},
                {"Name": "TransactionDate", "Value": 20261114091502},
                {"Name": "PhoneNumber", "Value": 254711000001},
            ]
        }
    return {"Body": {"stkCallback": callback}}


async def post_callback(
    api: IntegrationAPI, body: dict[str, Any], token: str = TOKEN
) -> Any:
    return await api.client.post(f"/api/v1/payments/stk/callback/{token}", json=body)


async def status_of(owner: Owner, gym_id: str, payment_id: str) -> dict[str, Any]:
    response = await owner.call("GET", f"/gyms/{gym_id}/payments/{payment_id}")
    assert response.status_code == 200, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


async def paid_until(owner: Owner, gym_id: str, member_id: str) -> str | None:
    detail = (await owner.call("GET", f"/gyms/{gym_id}/members/{member_id}")).json()
    value: str | None = detail["data"]["member"]["paid_until"]
    return value


async def test_a_prompt_is_sent_and_nothing_counts_until_mpesa_confirms(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)

    response = await request(owner, gym_id, member_id, plans["Monthly"])

    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["message"] == "Waiting for the member to enter their M-Pesa PIN."
    [push] = gateway.pushes
    assert (push["phone_number"], push["amount"]) == ("+254711000001", 5000)
    assert push["callback_url"].endswith(f"/api/v1/payments/stk/callback/{TOKEN}")
    # Daraja won't call back to URLs with these words in them.
    assert "mpesa" not in push["callback_url"].lower()
    assert "safaricom" not in push["callback_url"].lower()
    assert await paid_until(owner, gym_id, member_id) is None


async def test_a_confirmed_payment_activates_the_membership_once(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    payment_id = (await request(owner, gym_id, member_id, plans["Monthly"])).json()[
        "data"
    ]["payment_id"]

    response = await post_callback(api, callback_body("ws_CO_1"))

    assert response.json() == {"ResultCode": 0, "ResultDesc": "Accepted"}
    status = await status_of(owner, gym_id, payment_id)
    assert (status["status"], status["receipt"], status["paid_until"]) == (
        "completed",
        "TKE1ABC2DE",
        "2026-12-13",
    )
    assert await paid_until(owner, gym_id, member_id) == "2026-12-13"
    assert len(api.sms.texts) == 1 and api.sms.texts[0][1].startswith("Welcome")

    # Safaricom retries callbacks: the second one changes nothing.
    await post_callback(api, callback_body("ws_CO_1"))
    assert await paid_until(owner, gym_id, member_id) == "2026-12-13"
    assert len(api.sms.texts) == 1
    rows = await api.sql("SELECT count(*) FROM gym_memberships WHERE status = 'active'")
    assert rows == [(1,)]


async def test_dates_are_fixed_when_the_money_arrives_by_the_gyms_calendar(
    api: IntegrationAPI,
    storage: FakeStorage,
    gateway: FakeGateway,
    pinned_clock: PinnedClock,
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    await request(owner, gym_id, member_id, plans["Weekly"])

    # Paid at 00:30 on 15 Nov in Nairobi (still 14 Nov in UTC).
    pinned_clock.set("2026-11-14T21:30:00+00:00")
    await post_callback(api, callback_body("ws_CO_1", amount=1500))

    assert await paid_until(owner, gym_id, member_id) == "2026-11-21"


async def test_an_early_renewal_starts_after_the_current_period(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    await pay_cash(owner, gym_id, member_id, plan_id=plans["Monthly"])  # to 13 Dec
    await request(owner, gym_id, member_id, plans["Monthly"])

    await post_callback(api, callback_body("ws_CO_1"))

    assert await paid_until(owner, gym_id, member_id) == "2027-01-13"
    receipt = api.sms.texts[-1][1]
    assert "received KES 5,000" in receipt and "13 Jan 2027" in receipt


async def test_a_cancelled_prompt_fails_without_extending_anything(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    payment_id = (await request(owner, gym_id, member_id, plans["Monthly"])).json()[
        "data"
    ]["payment_id"]

    await post_callback(api, callback_body("ws_CO_1", code=1032))

    status = await status_of(owner, gym_id, payment_id)
    assert status["status"] == "failed"
    assert status["message"] == "The member cancelled the M-Pesa prompt."
    assert await paid_until(owner, gym_id, member_id) is None
    rows = await api.sql("SELECT status FROM gym_memberships")
    assert rows == [("cancelled",)]
    # A new prompt can be sent straight away.
    assert (
        await request(owner, gym_id, member_id, plans["Monthly"])
    ).status_code == 201


async def test_a_different_amount_is_not_activated(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    payment_id = (await request(owner, gym_id, member_id, plans["Monthly"])).json()[
        "data"
    ]["payment_id"]

    await post_callback(api, callback_body("ws_CO_1", amount=50))

    status = await status_of(owner, gym_id, payment_id)
    assert status["status"] == "failed"
    assert "different amount" in status["message"]
    assert status["receipt"] == "TKE1ABC2DE"
    assert await paid_until(owner, gym_id, member_id) is None


async def test_only_callbacks_with_the_secret_token_are_read(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    await request(owner, gym_id, member_id, plans["Monthly"])

    forged = await post_callback(api, callback_body("ws_CO_1"), token="guess" * 7)
    assert forged.status_code == 404
    assert await paid_until(owner, gym_id, member_id) is None

    # Unknown or unreadable results are acknowledged so Safaricom stops retrying.
    assert (await post_callback(api, callback_body("ws_CO_999"))).status_code == 200
    assert (await post_callback(api, {"hello": "world"})).status_code == 200


async def test_a_failed_push_is_reported_and_can_be_retried(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    gateway.push_error = MpesaError("request_rejected", provider_code="400.002.02")

    response = await request(owner, gym_id, member_id, plans["Monthly"])

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "MPESA_REQUEST_FAILED"
    rows = await api.sql("SELECT status FROM payments")
    assert rows == [("failed",)]
    gateway.push_error = None
    assert (
        await request(owner, gym_id, member_id, plans["Monthly"])
    ).status_code == 201


async def test_one_prompt_at_a_time_per_member(
    api: IntegrationAPI,
    storage: FakeStorage,
    gateway: FakeGateway,
    pinned_clock: PinnedClock,
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    await request(owner, gym_id, member_id, plans["Monthly"])

    again = await request(owner, gym_id, member_id, plans["Monthly"])
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "MPESA_PAYMENT_PENDING"

    pinned_clock.set("2026-11-14T06:04:00+00:00")
    assert (
        await request(owner, gym_id, member_id, plans["Monthly"])
    ).status_code == 201


async def test_switched_off_and_access_rules(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    app.dependency_overrides[get_mpesa_gateway] = lambda: None

    off = await request(owner, gym_id, member_id, plans["Monthly"])
    assert off.status_code == 503
    assert off.json()["error"]["code"] == "MPESA_NOT_CONFIGURED"

    app.dependency_overrides[get_mpesa_gateway] = FakeGateway
    other = await sign_in_owner(api, phone="0733000000")
    other_gym_id, _ = await gym_with_plans(other, storage)
    assert (
        await request(other, gym_id, member_id, plans["Monthly"])
    ).status_code == 403
    response = await request(other, other_gym_id, member_id, plans["Monthly"])
    assert response.status_code == 404


async def test_reconcile_settles_lost_callbacks_and_gives_up_on_silence(
    api: IntegrationAPI,
    storage: FakeStorage,
    gateway: FakeGateway,
    pinned_clock: PinnedClock,
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    paid = (await request(owner, gym_id, member_id, plans["Monthly"])).json()["data"]
    pinned_clock.set("2026-11-14T06:04:00+00:00")
    other = (
        await owner.call(
            "POST",
            f"/gyms/{gym_id}/members",
            json={"full_name": "Brian Kiprop", "phone_number": "0711000002"},
        )
    ).json()["data"]
    silent = (await request(owner, gym_id, other["id"], plans["Monthly"])).json()[
        "data"
    ]
    factory = async_sessionmaker(
        bind=api.engine, class_=AsyncSession, expire_on_commit=False
    )

    async def run() -> dict[str, int]:
        outcomes = await reconcile_pending(
            session_factory=factory,
            gateway=gateway,
            sms=api.sms,
            settings=api.settings,
            clock=pinned_clock,
        )
        return dict(outcomes)

    # The first callback was lost; Daraja's status query has the answer.
    gateway.query_results["ws_CO_1"] = StkResult(result_code=0, result_desc="ok")
    pinned_clock.set("2026-11-14T06:06:00+00:00")
    assert await run() == {"paid": 1, "still_waiting": 1}
    assert (await status_of(owner, gym_id, paid["payment_id"]))["status"] == "completed"

    # A late callback for the settled payment is ignored.
    await post_callback(api, callback_body("ws_CO_1"))
    assert await paid_until(owner, gym_id, member_id) == "2026-12-13"

    # No answer after the timeout: given up.
    pinned_clock.set("2026-11-14T06:30:00+00:00")
    assert await run() == {"timed_out": 1}
    status = await status_of(owner, gym_id, silent["payment_id"])
    assert status["status"] == "failed"
    assert status["message"] == "The member didn't answer the M-Pesa prompt in time."


async def test_prompts_sent_before_the_path_change_still_settle(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    payment_id = (await request(owner, gym_id, member_id, plans["Monthly"])).json()[
        "data"
    ]["payment_id"]

    response = await api.client.post(
        f"/api/v1/payments/mpesa/callback/{TOKEN}", json=callback_body("ws_CO_1")
    )

    assert response.json() == {"ResultCode": 0, "ResultDesc": "Accepted"}
    assert (await status_of(owner, gym_id, payment_id))["status"] == "completed"
    wrong = await api.client.post(
        "/api/v1/payments/mpesa/callback/wrong-token", json=callback_body("ws_CO_1")
    )
    assert wrong.status_code == 404
