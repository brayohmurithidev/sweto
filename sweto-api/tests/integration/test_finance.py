"""Finance tab (MVP build order, PR 9). Gyms are on Nairobi time (UTC+3)."""

from typing import Any

import pytest

from tests.integration.conftest import IntegrationAPI, PinnedClock
from tests.integration.test_gym_members import add_member, gym_with_plans, pay_cash
from tests.integration.test_gym_owner_journey import FakeStorage, Owner, sign_in_owner
from tests.integration.test_mpesa import (
    FakeGateway,
    callback_body,
    gateway,  # noqa: F401  (fixture)
    post_callback,
    request,
)

pytestmark = pytest.mark.usefixtures("pinned_clock")


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


async def finance(owner: Owner, gym_id: str, **params: Any) -> dict[str, Any]:
    response = await owner.call("GET", f"/gyms/{gym_id}/finance", params=params)
    assert response.status_code == 200, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


async def transactions(owner: Owner, gym_id: str, **params: Any) -> dict[str, Any]:
    response = await owner.call(
        "GET", f"/gyms/{gym_id}/finance/transactions", params=params
    )
    assert response.status_code == 200, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


async def test_a_month_splits_by_method_and_plan_with_a_trend(
    api: IntegrationAPI,
    storage: FakeStorage,
    gateway: FakeGateway,  # noqa: F811
    pinned_clock: PinnedClock,
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)

    # August and October: cash. Nothing in September.
    pinned_clock.set("2026-08-10T06:00:00+00:00")
    august = await add_member(owner, gym_id, "August Payer", "0711000009")
    await pay_cash(owner, gym_id, august["id"], plan_id=plans["Weekly"])  # 1,500
    pinned_clock.set("2026-10-05T06:00:00+00:00")
    october = await add_member(owner, gym_id, "October Payer", "0711000008")
    await pay_cash(owner, gym_id, october["id"], plan_id=plans["Monthly"])  # 5,000
    pinned_clock.set("2026-10-20T06:00:00+00:00")  # after the 14th: not compared
    await pay_cash(owner, gym_id, october["id"], plan_id=plans["Weekly"])  # 1,500

    # November so far: cash weekly, M-Pesa monthly, one cancelled prompt and
    # one still waiting.
    pinned_clock.set("2026-11-14T06:00:00+00:00")
    cash = await add_member(owner, gym_id, "Cash Member", "0711000001")
    await pay_cash(owner, gym_id, cash["id"], plan_id=plans["Weekly"])
    pinned_clock.set("2026-11-14T06:10:00+00:00")
    mpesa = await add_member(owner, gym_id, "Mpesa Member", "0711000002")
    await request(owner, gym_id, mpesa["id"], plans["Monthly"])
    await post_callback(api, callback_body("ws_CO_1"))  # paid, 5,000
    pinned_clock.set("2026-11-14T06:20:00+00:00")
    cancels = await add_member(owner, gym_id, "Cancels Prompt", "0711000003")
    await request(owner, gym_id, cancels["id"], plans["Monthly"])
    await post_callback(api, callback_body("ws_CO_2", code=1032))
    pinned_clock.set("2026-11-14T06:30:00+00:00")
    waits = await add_member(owner, gym_id, "Still Waiting", "0711000004")
    await request(owner, gym_id, waits["id"], plans["Weekly"])

    data = await finance(owner, gym_id)

    assert (data["month"], data["through"], data["is_current_month"]) == (
        "2026-11-01",
        "2026-11-14",
        True,
    )
    assert (data["total"], data["payments_count"]) == ("6500.00", 2)
    # 1–14 Oct only: the 20 Oct payment is after the same point last month.
    assert data["previous_month_total"] == "5000.00"
    assert data["change_percent"] == 30.0
    assert data["by_method"] == [
        {"method": "cash", "amount": "1500.00", "count": 1},
        {"method": "mpesa", "amount": "5000.00", "count": 1},
    ]
    assert data["by_plan"] == [
        {"plan_name": "Monthly", "amount": "5000.00", "count": 1},
        {"plan_name": "Weekly", "amount": "1500.00", "count": 1},
    ]
    assert data["trend"] == [
        {"month": "2026-06-01", "amount": "0"},
        {"month": "2026-07-01", "amount": "0"},
        {"month": "2026-08-01", "amount": "1500.00"},
        {"month": "2026-09-01", "amount": "0"},
        {"month": "2026-10-01", "amount": "6500.00"},
        {"month": "2026-11-01", "amount": "6500.00"},
    ]
    assert (data["failed_mpesa_count"], data["pending_mpesa_count"]) == (1, 1)

    # A finished month is compared with the whole month before.
    october_data = await finance(owner, gym_id, month="2026-10")
    assert (october_data["through"], october_data["is_current_month"]) == (
        "2026-10-31",
        False,
    )
    assert (october_data["total"], october_data["previous_month_total"]) == (
        "6500.00",
        "0",
    )
    assert october_data["change_percent"] is None
    assert october_data["trend"][-1] == {"month": "2026-10-01", "amount": "6500.00"}

    listed = await transactions(owner, gym_id)
    assert listed["total"] == 4
    rows = listed["transactions"]
    assert [(r["member_name"], r["status"]) for r in rows] == [
        ("Still Waiting", "pending"),
        ("Cancels Prompt", "failed"),
        ("Mpesa Member", "completed"),
        ("Cash Member", "completed"),
    ]
    paid = rows[2]
    assert (paid["method"], paid["amount"], paid["receipt"], paid["plan_name"]) == (
        "mpesa",
        "5000.00",
        "TKE1ABC2DE",
        "Monthly",
    )
    assert rows[3]["receipt"] is None and rows[3]["method"] == "cash"

    only_cash = await transactions(owner, gym_id, method="cash")
    assert [r["member_name"] for r in only_cash["transactions"]] == ["Cash Member"]
    completed = await transactions(owner, gym_id, status="completed", limit=1)
    assert (completed["total"], len(completed["transactions"])) == (2, 1)
    second = await transactions(owner, gym_id, status="completed", limit=1, offset=1)
    assert second["transactions"][0]["member_name"] == "Cash Member"


async def test_months_follow_the_gyms_midnight(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add_member(owner, gym_id)

    # 00:30 on 1 Nov in Nairobi, still 31 Oct in UTC: November money.
    pinned_clock.set("2026-10-31T21:30:00+00:00")
    await pay_cash(owner, gym_id, member["id"], plan_id=plans["Weekly"])

    november = await finance(owner, gym_id)
    assert (november["month"], november["total"]) == ("2026-11-01", "1500.00")
    assert november["trend"][-2:] == [
        {"month": "2026-10-01", "amount": "0"},
        {"month": "2026-11-01", "amount": "1500.00"},
    ]
    assert (await transactions(owner, gym_id, month="2026-10"))["total"] == 0
    assert (await transactions(owner, gym_id, month="2026-11"))["total"] == 1


async def test_an_empty_gym_shows_zeros_and_future_months_are_refused(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)

    data = await finance(owner, gym_id)

    assert (data["total"], data["payments_count"]) == ("0", 0)
    assert [m["amount"] for m in data["by_method"]] == ["0", "0"]
    assert data["by_plan"] == []
    assert len(data["trend"]) == 6
    assert (await transactions(owner, gym_id))["transactions"] == []

    future = await owner.call(
        "GET", f"/gyms/{gym_id}/finance", params={"month": "2026-12"}
    )
    assert future.status_code == 422
    assert future.json()["error"]["code"] == "INVALID_FINANCE_MONTH"
    bad = await owner.call(
        "GET", f"/gyms/{gym_id}/finance", params={"month": "2026-13"}
    )
    assert bad.status_code == 422


async def test_only_this_gyms_owner_or_manager_sees_it(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    other = await sign_in_owner(api, phone="0733000000")
    await gym_with_plans(other, storage)
    receptionist = await sign_in_owner(api, phone="0744000000")
    await api.sql(
        "INSERT INTO gym_staff (id, gym_id, user_id, role, status, is_primary_owner) "
        "SELECT gen_random_uuid(), :gym_id, id, 'receptionist', 'active', false "
        "FROM users WHERE phone_number = '+254744000000'",
        gym_id=gym_id,
    )

    for path in ("finance", "finance/transactions"):
        for caller in (other, receptionist):
            response = await caller.call("GET", f"/gyms/{gym_id}/{path}")
            assert response.status_code == 403
        anonymous = await api.client.get(f"/api/v1/gyms/{gym_id}/{path}")
        assert anonymous.status_code == 401
