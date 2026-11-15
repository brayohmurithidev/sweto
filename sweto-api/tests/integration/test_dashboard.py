"""Home tab numbers (MVP build order, PR 7). Gyms are on Nairobi time (UTC+3)."""

from typing import Any

import pytest

from tests.integration.conftest import IntegrationAPI, PinnedClock
from tests.integration.test_check_ins import check_in, issue_code
from tests.integration.test_gym_members import add_member, gym_with_plans, pay_cash
from tests.integration.test_gym_owner_journey import FakeStorage, Owner, sign_in_owner

pytestmark = pytest.mark.usefixtures("pinned_clock")


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


async def dashboard(owner: Owner, gym_id: str) -> dict[str, Any]:
    response = await owner.call("GET", f"/gyms/{gym_id}/dashboard")
    assert response.status_code == 200, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


async def test_the_home_numbers_add_up(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)

    # Last month: one payment of KES 1,500.
    pinned_clock.set("2026-10-20T06:00:00+00:00")
    october = await add_member(owner, gym_id, "October Payer", "0711000009")
    await pay_cash(owner, gym_id, october["id"], plan_id=plans["Weekly"])  # to 26 Oct

    # Today, 14 Nov: a monthly and a weekly member, and one who never paid.
    pinned_clock.set("2026-11-14T06:00:00+00:00")
    monthly = await add_member(owner, gym_id, "Monthly Member", "0711000001")
    weekly = await add_member(owner, gym_id, "Weekly Member", "0711000002")
    await add_member(owner, gym_id, "Never Paid", "0711000003")
    await pay_cash(owner, gym_id, monthly["id"], plan_id=plans["Monthly"])  # 5,000
    await pay_cash(owner, gym_id, weekly["id"], plan_id=plans["Weekly"])  # 1,500

    code = (await issue_code(owner, gym_id, monthly["id"]))["code"]
    pinned_clock.set("2026-11-14T07:00:00+00:00")
    await check_in(owner, gym_id, code)
    await check_in(owner, gym_id, code)  # back the same day: not a second visit
    await check_in(owner, gym_id, "ZZZZ-ZZZZ")  # refused

    data = await dashboard(owner, gym_id)

    assert data["gym_name"] == "FlexFit Westlands"
    assert data["today"] == "2026-11-14"
    assert (data["active_members"], data["expiring_members"]) == (2, 1)
    assert data["check_ins_today"] == 1
    revenue = data["revenue"]
    assert (revenue["this_month"], revenue["last_month"]) == ("6500.00", "1500.00")
    assert revenue["change_percent"] == 333.3
    assert len(revenue["daily"]) == 14
    assert revenue["daily"][0]["date"] == "2026-11-01"
    assert revenue["daily"][-1] == {"date": "2026-11-14", "amount": "6500.00"}
    assert all(day["amount"] == "0" for day in revenue["daily"][:-1])

    activity = data["recent_activity"]
    assert len(activity) == 8
    times = [item["at"] for item in activity]
    assert times == sorted(times, reverse=True)
    refused = [i for i in activity if i["kind"] == "check_in" and not i["ok"]]
    assert refused and refused[0]["detail"] == "Refused: unknown code"
    assert {item["kind"] for item in activity} == {
        "check_in",
        "payment",
        "member_added",
    }
    payment = next(i for i in activity if i["kind"] == "payment")
    assert payment["detail"].startswith("Paid KES ")


async def test_months_follow_the_gyms_midnight(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add_member(owner, gym_id)

    # 00:30 on 1 Nov in Nairobi, still 31 Oct in UTC: November money.
    pinned_clock.set("2026-10-31T21:30:00+00:00")
    await pay_cash(owner, gym_id, member["id"], plan_id=plans["Weekly"])

    revenue = (await dashboard(owner, gym_id))["revenue"]

    assert (revenue["this_month"], revenue["last_month"]) == ("1500.00", "0")
    assert revenue["change_percent"] is None
    assert revenue["daily"] == [{"date": "2026-11-01", "amount": "1500.00"}]


async def test_an_empty_gym_shows_zeros(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)

    data = await dashboard(owner, gym_id)

    assert (data["active_members"], data["check_ins_today"]) == (0, 0)
    assert data["revenue"]["this_month"] == "0"
    assert data["recent_activity"] == []


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

    for caller in (other, receptionist):
        response = await caller.call("GET", f"/gyms/{gym_id}/dashboard")
        assert response.status_code == 403
    assert (await api.client.get(f"/api/v1/gyms/{gym_id}/dashboard")).status_code == 401
