"""Pay now, start later: a member pays on Saturday and starts on Monday.

The pinned clock starts on Saturday 14 Nov 2026, 09:00 in Nairobi.
"""

from typing import Any

import pytest

from tests.integration.conftest import IntegrationAPI, PinnedClock
from tests.integration.test_check_ins import check_in, issue_code
from tests.integration.test_gym_members import gym_with_plans, listed, pay_cash
from tests.integration.test_gym_owner_journey import FakeStorage, Owner, sign_in_owner

pytestmark = pytest.mark.usefixtures("pinned_clock")


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


async def member_detail(owner: Owner, gym_id: str, member_id: str) -> dict[str, Any]:
    response = await owner.call("GET", f"/gyms/{gym_id}/members/{member_id}")
    assert response.status_code == 200, response.json()
    data: dict[str, Any] = response.json()["data"]["member"]
    return data


async def dashboard(owner: Owner, gym_id: str) -> dict[str, Any]:
    response = await owner.call("GET", f"/gyms/{gym_id}/dashboard")
    assert response.status_code == 200, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


async def test_paid_on_saturday_starts_on_monday(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    added = await owner.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={
            "full_name": "Starts Monday",
            "phone_number": "0711000001",
            "sms_consent": True,
        },
    )
    member_id = added.json()["data"]["id"]

    paid = await pay_cash(
        owner, gym_id, member_id, plan_id=plans["Weekly"], starts_on="2026-11-16"
    )

    assert paid.status_code == 201, paid.json()
    data = paid.json()["data"]
    assert (data["membership"]["starts_on"], data["membership"]["ends_on"]) == (
        "2026-11-16",
        "2026-11-22",
    )
    member = await member_detail(owner, gym_id, member_id)
    assert (member["standing"], member["starts_on"], member["paid_until"]) == (
        "upcoming",
        "2026-11-16",
        "2026-11-22",
    )
    [(_, welcome)] = api.sms.texts
    assert "Starts 16 Nov 2026, paid until 22 Nov 2026." in welcome

    # Paid members are on the Active tab, but not expiring or counted yet.
    assert await listed(owner, gym_id, standing="active") == ["Starts Monday"]
    assert await listed(owner, gym_id, standing="upcoming") == ["Starts Monday"]
    assert await listed(owner, gym_id, standing="expiring") == []
    home = await dashboard(owner, gym_id)
    assert (home["active_members"], home["expiring_members"]) == (0, 0)
    # The money counts on the day it was received.
    assert home["revenue"]["this_month"] == "1500.00"

    # Saturday at the door: not yet.
    code = (await issue_code(owner, gym_id, member_id))["code"]
    early = await check_in(owner, gym_id, code)
    assert (early["result"], early["allowed"]) == ("not_started", False)
    assert early["message"] == "Starts Monday's membership starts on 16 Nov 2026."
    assert early["member"]["standing"] == "upcoming"

    # Monday: in, and counted.
    pinned_clock.set("2026-11-16T05:00:00+00:00")
    monday = await check_in(owner, gym_id, code)
    assert (monday["result"], monday["allowed"]) == ("allowed", True)
    member = await member_detail(owner, gym_id, member_id)
    assert (member["standing"], member["starts_on"]) == ("expiring", "2026-11-16")
    home = await dashboard(owner, gym_id)
    assert (home["active_members"], home["expiring_members"]) == (1, 1)
    assert await listed(owner, gym_id, standing="upcoming") == []


async def test_a_start_date_at_most_30_days_ahead(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    added = await owner.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={"full_name": "Far Ahead", "phone_number": "0711000002"},
    )
    member_id = added.json()["data"]["id"]

    too_far = await pay_cash(
        owner, gym_id, member_id, plan_id=plans["Monthly"], starts_on="2026-12-15"
    )
    assert too_far.status_code == 422
    assert too_far.json()["error"]["message"] == (
        "The start date can be at most 30 days ahead."
    )

    limit = await pay_cash(
        owner, gym_id, member_id, plan_id=plans["Monthly"], starts_on="2026-12-14"
    )
    assert limit.status_code == 201, limit.json()

    # A renewal while paid ahead queues after the paid period, as before.
    renewal = await pay_cash(owner, gym_id, member_id, plan_id=plans["Monthly"])
    assert renewal.status_code == 201, renewal.json()
    assert renewal.json()["data"]["membership"]["starts_on"] == "2027-01-14"
