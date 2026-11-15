"""Each gym's own M-Pesa till (MVP build order, PR 8)."""

from typing import Any

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.integrations.mpesa.dependencies import get_mpesa_gateway
from app.jobs.mpesa_reconcile import reconcile_pending
from app.main import app
from tests.integration.conftest import IntegrationAPI, PinnedClock
from tests.integration.test_gym_owner_journey import FakeStorage, Owner
from tests.integration.test_mpesa import FakeGateway, member_with_plan, request

pytestmark = pytest.mark.usefixtures("pinned_clock")
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
TILL = {
    "account_type": "till",
    "shortcode": "7654321",
    "till_number": "5123456",
    "passkey": PASSKEY,
}


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


@pytest.fixture
def gateway(api: IntegrationAPI) -> FakeGateway:
    fake = FakeGateway()
    app.dependency_overrides[get_mpesa_gateway] = lambda: fake
    api.settings.mpesa_callback_token = SecretStr("callback-token-for-tests-0123456789")
    api.settings.mpesa_credentials_key = SecretStr(Fernet.generate_key().decode())
    api.settings.mpesa_mode = "production"
    return fake


async def save(owner: Owner, gym_id: str, body: dict[str, Any]) -> Any:
    return await owner.call("PUT", f"/gyms/{gym_id}/mpesa-account", json=body)


async def test_the_owner_saves_a_till_and_the_passkey_stays_secret(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, _, _ = await member_with_plan(api, storage)
    before = (await owner.call("GET", f"/gyms/{gym_id}/mpesa-account")).json()["data"]
    assert (before["configured"], before["mode"]) == (False, "production")

    saved = await save(owner, gym_id, TILL)

    assert saved.status_code == 200, saved.json()
    data = saved.json()["data"]
    assert (data["account_type"], data["shortcode"], data["till_number"]) == (
        "till",
        "7654321",
        "5123456",
    )
    assert data["passkey_saved"] is True
    assert PASSKEY not in saved.text
    [(stored,)] = await api.sql("SELECT passkey_encrypted FROM gym_mpesa_accounts")
    assert PASSKEY not in str(stored)
    key = api.settings.mpesa_credentials_key
    assert key is not None
    assert Fernet(key.get_secret_value().encode()).decrypt(str(stored).encode()) == (
        PASSKEY.encode()
    )

    # Later saves can leave the passkey out to keep it.
    moved = await save(
        owner, gym_id, {**TILL, "till_number": "5999999", "passkey": None}
    )
    assert moved.json()["data"]["till_number"] == "5999999"
    [(kept,)] = await api.sql("SELECT passkey_encrypted FROM gym_mpesa_accounts")
    assert kept == stored


async def test_invalid_tills_are_refused(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, _, _ = await member_with_plan(api, storage)

    no_till = await save(owner, gym_id, {**TILL, "till_number": None})
    letters = await save(owner, gym_id, {**TILL, "shortcode": "ABC123"})
    no_passkey = await save(owner, gym_id, {**TILL, "passkey": None})

    assert no_till.status_code == 422
    assert letters.status_code == 422
    assert no_passkey.status_code == 422
    assert no_passkey.json()["error"]["code"] == "INVALID_MEMBERSHIP_PAYMENT"


async def test_only_the_owner_changes_where_money_goes(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, _, _ = await member_with_plan(api, storage)
    from tests.integration.test_gym_owner_journey import sign_in_owner

    manager = await sign_in_owner(api, phone="0744000000")
    await api.sql(
        "INSERT INTO gym_staff (id, gym_id, user_id, role, status, is_primary_owner) "
        "SELECT gen_random_uuid(), :gym_id, id, 'manager', 'active', false "
        "FROM users WHERE phone_number = '+254744000000'",
        gym_id=gym_id,
    )

    assert (
        await manager.call("GET", f"/gyms/{gym_id}/mpesa-account")
    ).status_code == 200
    assert (await save(manager, gym_id, TILL)).status_code == 403
    other = await sign_in_owner(api, phone="0733000000")
    assert (await save(other, gym_id, TILL)).status_code == 403


async def test_prompts_go_to_the_gyms_own_till(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)

    # Production: no till yet, no prompt.
    refused = await request(owner, gym_id, member_id, plans["Monthly"])
    assert refused.status_code == 503
    assert "M-Pesa till" in refused.json()["error"]["message"]
    assert gateway.pushes == []

    await save(owner, gym_id, TILL)
    sent = await request(owner, gym_id, member_id, plans["Monthly"])

    assert sent.status_code == 201, sent.json()
    account = gateway.pushes[0]["account"]
    assert (account.shortcode, account.party_b, account.transaction_type) == (
        "7654321",
        "5123456",
        "CustomerBuyGoodsOnline",
    )
    assert account.passkey == PASSKEY


async def test_reconcile_queries_with_the_gyms_till(
    api: IntegrationAPI,
    storage: FakeStorage,
    gateway: FakeGateway,
    pinned_clock: PinnedClock,
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    await save(owner, gym_id, {**TILL, "account_type": "paybill", "till_number": None})
    await request(owner, gym_id, member_id, plans["Monthly"])
    pinned_clock.set("2026-11-14T06:02:00+00:00")

    await reconcile_pending(
        session_factory=async_sessionmaker(
            bind=api.engine, class_=AsyncSession, expire_on_commit=False
        ),
        gateway=gateway,
        sms=api.sms,
        settings=api.settings,
        clock=pinned_clock,
    )

    [account] = gateway.queried_accounts
    assert (account.shortcode, account.party_b, account.transaction_type) == (
        "7654321",
        "7654321",
        "CustomerPayBillOnline",
    )
