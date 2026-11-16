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
CONSUMER_KEY = "fake-consumer-key-xxxxxxxxxx"
CONSUMER_SECRET = "fake-consumer-secret-xxxxxxxxxx"
TILL = {
    "account_type": "till",
    "shortcode": "7654321",
    "till_number": "5123456",
    "passkey": PASSKEY,
    "consumer_key": CONSUMER_KEY,
    "consumer_secret": CONSUMER_SECRET,
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
    assert data["app_keys_saved"] is True
    for secret in (PASSKEY, CONSUMER_KEY, CONSUMER_SECRET):
        assert secret not in saved.text
    [(key_stored, secret_stored)] = await api.sql(
        "SELECT consumer_key_encrypted, consumer_secret_encrypted "
        "FROM gym_mpesa_accounts"
    )
    assert CONSUMER_KEY not in str(key_stored)
    assert CONSUMER_SECRET not in str(secret_stored)
    [(stored,)] = await api.sql("SELECT passkey_encrypted FROM gym_mpesa_accounts")
    assert PASSKEY not in str(stored)
    key = api.settings.mpesa_credentials_key
    assert key is not None
    assert Fernet(key.get_secret_value().encode()).decrypt(str(stored).encode()) == (
        PASSKEY.encode()
    )

    # Later saves can leave the passkey out to keep it.
    moved = await save(
        owner,
        gym_id,
        {
            **TILL,
            "till_number": "5999999",
            "passkey": None,
            "consumer_key": None,
            "consumer_secret": None,
        },
    )
    assert moved.json()["data"]["till_number"] == "5999999"
    assert moved.json()["data"]["app_keys_saved"] is True
    [(kept, key_kept)] = await api.sql(
        "SELECT passkey_encrypted, consumer_key_encrypted FROM gym_mpesa_accounts"
    )
    assert (kept, key_kept) == (stored, key_stored)


async def test_invalid_tills_are_refused(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, _, _ = await member_with_plan(api, storage)

    no_till = await save(owner, gym_id, {**TILL, "till_number": None})
    letters = await save(owner, gym_id, {**TILL, "shortcode": "ABC123"})
    no_passkey = await save(owner, gym_id, {**TILL, "passkey": None})
    # Production without SWETO's own app: each gym brings its Daraja keys.
    no_keys = await save(
        owner, gym_id, {**TILL, "consumer_key": None, "consumer_secret": None}
    )
    half_keys = await save(owner, gym_id, {**TILL, "consumer_secret": None})

    assert no_till.status_code == 422
    assert letters.status_code == 422
    assert no_passkey.status_code == 422
    assert no_passkey.json()["error"]["code"] == "INVALID_MEMBERSHIP_PAYMENT"
    assert no_keys.status_code == 422
    assert "Daraja app" in no_keys.json()["error"]["message"]
    assert half_keys.status_code == 422
    assert "both" in half_keys.json()["error"]["message"]


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
    # Each gym's prompts go through that gym's own Daraja app.
    assert (account.consumer_key, account.consumer_secret) == (
        CONSUMER_KEY,
        CONSUMER_SECRET,
    )


async def test_tills_saved_before_app_keys_ask_for_them_in_production(
    api: IntegrationAPI, storage: FakeStorage, gateway: FakeGateway
) -> None:
    owner, gym_id, member_id, plans = await member_with_plan(api, storage)
    await save(owner, gym_id, TILL)
    # As a till saved before gyms had their own Daraja apps.
    await api.sql(
        "UPDATE gym_mpesa_accounts "
        "SET consumer_key_encrypted = NULL, consumer_secret_encrypted = NULL"
    )

    refused = await request(owner, gym_id, member_id, plans["Monthly"])

    assert refused.status_code == 503
    assert "Daraja app keys" in refused.json()["error"]["message"]
    assert gateway.pushes == []
    data = (await owner.call("GET", f"/gyms/{gym_id}/mpesa-account")).json()["data"]
    assert data["app_keys_saved"] is False


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
    assert account.consumer_key == CONSUMER_KEY
