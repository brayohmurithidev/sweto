"""Who did what: the activity log and each staff member's day."""

import pytest

from tests.integration.conftest import IntegrationAPI
from tests.integration.test_check_ins import check_in, paid_member
from tests.integration.test_gym_members import add_member, gym_with_plans
from tests.integration.test_gym_owner_journey import FakeStorage, sign_in_owner
from tests.integration.test_gym_staff import hire

pytestmark = pytest.mark.usefixtures("pinned_clock")


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


async def test_the_log_says_who_did_what_and_follows_one_person(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    await add_member(owner, gym_id, "Owner Added", "0711000009")
    desk, desk_row = await hire(api, owner, gym_id, "receptionist", "0744000000")
    # The receptionist adds a member, takes cash and checks them in.
    _, code = await paid_member(desk, gym_id, plans["Monthly"], phone="0711000001")
    assert (await check_in(desk, gym_id, code))["result"] == "allowed"

    response = await owner.call("GET", f"/gyms/{gym_id}/activity")
    assert response.status_code == 200, response.json()
    page = response.json()["data"]
    kinds = {(i["kind"], i["by_name"]) for i in page["items"]}
    assert ("check_in", "Wanjiku Kamau") in kinds
    assert ("payment", "Wanjiku Kamau") in kinds
    assert ("member_added", "Wanjiku Kamau") in kinds
    assert page["has_more"] is False

    mine = await owner.call(
        "GET", f"/gyms/{gym_id}/activity", params={"by": desk_row["user_id"]}
    )
    items = mine.json()["data"]["items"]
    assert len(items) == 3
    assert {i["by_user_id"] for i in items} == {desk_row["user_id"]}
    assert "Owner Added" not in {i["member_name"] for i in items}

    # Paging: two pages cover the four events without repeats.
    pages = [
        (
            await owner.call(
                "GET", f"/gyms/{gym_id}/activity", params={"limit": 2, "offset": n}
            )
        ).json()["data"]
        for n in (0, 2)
    ]
    assert [p["has_more"] for p in pages] == [True, False]
    seen = [(i["kind"], i["member_name"]) for p in pages for i in p["items"]]
    assert len(seen) == len(set(seen)) == 4

    # Home shows the same names.
    home = (await owner.call("GET", f"/gyms/{gym_id}/dashboard")).json()["data"]
    assert home["recent_activity"][0]["by_name"] == "Wanjiku Kamau"


async def test_only_owner_and_manager_see_the_log(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    desk, _ = await hire(api, owner, gym_id, "receptionist", "0744000000")
    manager, _ = await hire(api, owner, gym_id, "manager", "0766000000")

    url = f"/gyms/{gym_id}/activity"
    assert (await desk.call("GET", url)).status_code == 403
    assert (await manager.call("GET", url)).status_code == 200


async def test_the_staff_list_shows_each_persons_day(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    desk, desk_row = await hire(api, owner, gym_id, "receptionist", "0744000000")
    _, code = await paid_member(desk, gym_id, plans["Monthly"], phone="0711000001")
    await check_in(desk, gym_id, code)

    staff = (await owner.call("GET", f"/gyms/{gym_id}/staff")).json()["data"]
    by_id = {s["id"]: s for s in staff["staff"]}
    day = by_id[desk_row["id"]]["today"]
    assert day["payments"] == 1
    assert float(day["cash"]) == 5000
    assert float(day["mpesa"]) == 0
    assert day["check_ins"] == 1
    owner_day = staff["staff"][0]["today"]
    assert (owner_day["payments"], owner_day["check_ins"]) == (0, 0)
