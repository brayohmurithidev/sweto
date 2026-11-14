"""Gym members, memberships and cash payments (MVP build order, PR 2).

The clock is pinned so dates are exact. Gyms default to Africa/Nairobi
(UTC+3): 21:00 UTC is midnight at the gym.
"""

from typing import Any

import pytest

from tests.integration.conftest import IntegrationAPI, PinnedClock
from tests.integration.test_gym_owner_journey import (
    FakeStorage,
    Owner,
    complete_profile,
    sign_in_owner,
)

pytestmark = pytest.mark.usefixtures("pinned_clock")


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


PLANS = {
    "day_passes": [{"name": "Day Pass", "amount": "500.00"}],
    "membership_plans": [
        {"name": "Monthly", "amount": "5000.00", "billing_period": "monthly"},
        {"name": "Weekly", "amount": "1500.00", "billing_period": "weekly"},
    ],
}


async def gym_with_plans(
    owner: Owner, storage: FakeStorage
) -> tuple[str, dict[str, str]]:
    gym_id = await complete_profile(owner, storage)
    response = await owner.call("PUT", f"/gyms/{gym_id}/pricing", json=PLANS)
    assert response.status_code == 200, response.json()
    plans = response.json()["data"]["membership_plans"]
    return gym_id, {plan["name"]: plan["id"] for plan in plans}


async def add_member(
    owner: Owner, gym_id: str, name: str = "Achieng Otieno", phone: str = "0711000001"
) -> dict[str, Any]:
    response = await owner.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={"full_name": name, "phone_number": phone},
    )
    assert response.status_code == 201, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


async def pay_cash(owner: Owner, gym_id: str, member_id: str, **body: Any) -> Any:
    return await owner.call(
        "POST", f"/gyms/{gym_id}/members/{member_id}/payments/cash", json=body
    )


async def member(owner: Owner, gym_id: str, member_id: str) -> dict[str, Any]:
    response = await owner.call("GET", f"/gyms/{gym_id}/members/{member_id}")
    assert response.status_code == 200, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


async def listed(owner: Owner, gym_id: str, **params: Any) -> list[str]:
    response = await owner.call("GET", f"/gyms/{gym_id}/members", params=params)
    assert response.status_code == 200, response.json()
    return [item["full_name"] for item in response.json()["data"]["members"]]


async def test_owner_adds_lists_and_searches_members(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)

    added = await add_member(owner, gym_id, "  Achieng   Otieno ", "0711 000 001")
    await add_member(owner, gym_id, "Brian Kiprop", "+254722000002")

    assert added["full_name"] == "Achieng Otieno"
    assert added["phone_number"] == "+254711000001"
    assert added["standing"] == "no_membership"
    assert added["paid_until"] is None
    assert await listed(owner, gym_id) == ["Achieng Otieno", "Brian Kiprop"]
    assert await listed(owner, gym_id, search="kip") == ["Brian Kiprop"]
    # A locally typed number finds the stored E.164 one.
    assert await listed(owner, gym_id, search="0711 000") == ["Achieng Otieno"]

    page = await owner.call("GET", f"/gyms/{gym_id}/members", params={"limit": 1})
    body = page.json()["data"]
    assert body["total"] == 2
    assert [m["full_name"] for m in body["members"]] == ["Achieng Otieno"]


async def test_phone_numbers_are_unique_per_gym_and_must_be_mobile(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    first = await add_member(owner, gym_id, phone="0711000001")
    second = await add_member(owner, gym_id, "Brian Kiprop", "0722000002")

    duplicate = await owner.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={"full_name": "Same Phone", "phone_number": "+254 711 000001"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "MEMBER_PHONE_TAKEN"

    moved = await owner.call(
        "PATCH",
        f"/gyms/{gym_id}/members/{second['id']}",
        json={"phone_number": "0711000001"},
    )
    assert moved.status_code == 409

    # Keeping your own number is not a clash.
    renamed = await owner.call(
        "PATCH",
        f"/gyms/{gym_id}/members/{first['id']}",
        json={"full_name": "Achieng O.", "phone_number": "0711000001"},
    )
    assert renamed.status_code == 200, renamed.json()
    assert renamed.json()["data"]["full_name"] == "Achieng O."

    landline = await owner.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={"full_name": "Office Line", "phone_number": "020 2222222"},
    )
    assert landline.status_code == 422
    assert landline.json()["error"]["code"] == "INVALID_PHONE_NUMBER"

    # The same person can be a member of another gym.
    other = await sign_in_owner(api, phone="0733000000")
    other_gym_id, _ = await gym_with_plans(other, storage)
    await add_member(other, other_gym_id, phone="0711000001")


async def test_cash_payments_create_and_renew_memberships(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    added = await add_member(owner, gym_id)

    first = await pay_cash(owner, gym_id, added["id"], plan_id=plans["Monthly"])
    assert first.status_code == 201, first.json()
    membership = first.json()["data"]["membership"]
    assert (membership["starts_on"], membership["ends_on"]) == (
        "2026-11-14",
        "2026-12-13",
    )
    assert membership["amount"] == "5000.00"
    assert membership["status"] == "active"
    payment = membership["payments"][0]
    assert (payment["method"], payment["status"]) == ("cash", "completed")
    assert payment["recorded_by_user_id"] is not None

    # Paying early never loses days: the renewal starts after the last day.
    renewal = await pay_cash(
        owner, gym_id, added["id"], plan_id=plans["Monthly"], amount="4500"
    )
    assert renewal.status_code == 201, renewal.json()
    data = renewal.json()["data"]
    assert (data["membership"]["starts_on"], data["membership"]["ends_on"]) == (
        "2026-12-14",
        "2027-01-13",
    )
    assert data["membership"]["amount"] == "4500.00"
    assert data["member"]["paid_until"] == "2027-01-13"
    assert data["member"]["standing"] == "active"

    detail = await member(owner, gym_id, added["id"])
    assert [m["starts_on"] for m in detail["memberships"]] == [
        "2026-12-14",
        "2026-11-14",
    ]


async def test_a_lapsed_member_renews_from_today(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    added = await add_member(owner, gym_id)
    assert (
        await pay_cash(owner, gym_id, added["id"], plan_id=plans["Weekly"])
    ).status_code == 201

    pinned_clock.set("2026-12-01T06:00:00+00:00")
    detail = await member(owner, gym_id, added["id"])
    assert detail["member"]["standing"] == "expired"
    assert detail["memberships"][0]["status"] == "expired"

    renewal = await pay_cash(owner, gym_id, added["id"], plan_id=plans["Weekly"])
    assert renewal.status_code == 201, renewal.json()
    membership = renewal.json()["data"]["membership"]
    assert (membership["starts_on"], membership["ends_on"]) == (
        "2026-12-01",
        "2026-12-07",
    )


async def test_a_membership_ends_at_the_gyms_midnight(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    added = await add_member(owner, gym_id)
    await pay_cash(owner, gym_id, added["id"], plan_id=plans["Monthly"])  # to 13 Dec

    # 23:59:59 on 13 Dec in Nairobi: the last moment of the last day.
    pinned_clock.set("2026-12-13T20:59:59+00:00")
    assert (await member(owner, gym_id, added["id"]))["member"][
        "standing"
    ] == "expiring"
    assert await listed(owner, gym_id, standing="expired") == []

    # Midnight in Nairobi, still 13 Dec in UTC.
    pinned_clock.set("2026-12-13T21:00:00+00:00")
    assert (await member(owner, gym_id, added["id"]))["member"]["standing"] == "expired"
    assert await listed(owner, gym_id, standing="expired") == ["Achieng Otieno"]
    assert await listed(owner, gym_id, standing="active") == []


async def test_standing_filters_split_active_expiring_expired_and_unpaid(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    lapsed = await add_member(owner, gym_id, "Lapsed", "0711000001")
    await pay_cash(owner, gym_id, lapsed["id"], plan_id=plans["Weekly"])
    pinned_clock.set("2026-11-21T06:00:00+00:00")  # lapsed ended 20 Nov

    weekly = await add_member(owner, gym_id, "Weekly", "0711000002")
    monthly = await add_member(owner, gym_id, "Monthly", "0711000003")
    await add_member(owner, gym_id, "Unpaid", "0711000004")
    await pay_cash(owner, gym_id, weekly["id"], plan_id=plans["Weekly"])  # to 27 Nov
    await pay_cash(owner, gym_id, monthly["id"], plan_id=plans["Monthly"])  # to 20 Dec

    assert await listed(owner, gym_id, standing="active") == ["Monthly", "Weekly"]
    # Ends within 7 days, counting today: 21 to 27 Nov.
    assert await listed(owner, gym_id, standing="expiring") == ["Weekly"]
    assert await listed(owner, gym_id, standing="expired") == ["Lapsed"]
    assert await listed(owner, gym_id, standing="no_membership") == ["Unpaid"]


async def test_a_start_date_can_be_backdated_for_members_who_paid_before(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    added = await add_member(owner, gym_id)
    monthly = plans["Monthly"]

    for starts_on in ["2026-11-15", "2026-08-15"]:  # future; more than 90 days back
        response = await pay_cash(
            owner, gym_id, added["id"], plan_id=monthly, starts_on=starts_on
        )
        assert response.status_code == 422, starts_on
        assert response.json()["error"]["code"] == "INVALID_MEMBERSHIP_PAYMENT"

    paid = await pay_cash(
        owner, gym_id, added["id"], plan_id=monthly, starts_on="2026-11-01"
    )
    assert paid.status_code == 201, paid.json()
    assert paid.json()["data"]["membership"]["ends_on"] == "2026-11-30"

    # While covered, a start date would leave a gap or an overlap.
    again = await pay_cash(
        owner, gym_id, added["id"], plan_id=monthly, starts_on="2026-11-14"
    )
    assert again.status_code == 422


async def test_archived_members_keep_history_and_can_be_restored(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    added = await add_member(owner, gym_id)
    await pay_cash(owner, gym_id, added["id"], plan_id=plans["Monthly"])

    archived = await owner.call("POST", f"/gyms/{gym_id}/members/{added['id']}/archive")
    assert archived.status_code == 200, archived.json()
    assert archived.json()["data"]["status"] == "archived"
    assert await listed(owner, gym_id) == []
    assert await listed(owner, gym_id, status="archived") == ["Achieng Otieno"]
    assert len((await member(owner, gym_id, added["id"]))["memberships"]) == 1

    blocked = await pay_cash(owner, gym_id, added["id"], plan_id=plans["Monthly"])
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "MEMBER_ARCHIVED"
    readd = await owner.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={"full_name": "Again", "phone_number": "0711000001"},
    )
    assert readd.status_code == 409

    restored = await owner.call("POST", f"/gyms/{gym_id}/members/{added['id']}/restore")
    assert restored.json()["data"]["status"] == "active"
    assert await listed(owner, gym_id) == ["Achieng Otieno"]


async def test_only_this_gyms_owner_or_manager_can_manage_its_members(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    added = await add_member(owner, gym_id)
    other = await sign_in_owner(api, phone="0733000000")
    other_gym_id, _ = await gym_with_plans(other, storage)
    base = f"/gyms/{gym_id}/members"

    # Another gym's owner: no access to this gym at all.
    for method, path in [
        ("GET", base),
        ("GET", f"{base}/{added['id']}"),
        ("POST", f"{base}/{added['id']}/archive"),
    ]:
        response = await other.call(method, path)
        assert response.status_code == 403, (method, path)

    # Through their own gym, this gym's member does not exist.
    response = await other.call("GET", f"/gyms/{other_gym_id}/members/{added['id']}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MEMBER_NOT_FOUND"
    response = await pay_cash(
        other, other_gym_id, added["id"], plan_id=plans["Monthly"]
    )
    assert response.status_code == 404

    # A plan from another gym cannot be sold here.
    other_plan = (await other.call("GET", f"/gyms/{other_gym_id}/pricing")).json()[
        "data"
    ]["membership_plans"][0]["id"]
    response = await pay_cash(owner, gym_id, added["id"], plan_id=other_plan)
    assert response.status_code == 422

    # Receptionists can't manage members; managers can.
    staff = await sign_in_owner(api, phone="0744000000")
    await api.sql(
        "INSERT INTO gym_staff (id, gym_id, user_id, role, status, is_primary_owner) "
        "SELECT gen_random_uuid(), :gym_id, id, 'receptionist', 'active', false "
        "FROM users WHERE phone_number = '+254744000000'",
        gym_id=gym_id,
    )
    assert (await staff.call("GET", base)).status_code == 403
    await api.sql(
        "UPDATE gym_staff SET role = 'manager' WHERE gym_id = :gym_id "
        "AND user_id = (SELECT id FROM users WHERE phone_number = '+254744000000')",
        gym_id=gym_id,
    )
    assert (await staff.call("GET", base)).status_code == 200

    assert (await api.client.get(f"/api/v1{base}")).status_code == 401


async def test_history_survives_plan_edits_and_removal(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    added = await add_member(owner, gym_id)
    await pay_cash(owner, gym_id, added["id"], plan_id=plans["Monthly"])

    response = await owner.call(
        "PUT",
        f"/gyms/{gym_id}/pricing",
        json={"day_passes": PLANS["day_passes"], "membership_plans": []},
    )
    assert response.status_code == 200, response.json()

    history = (await member(owner, gym_id, added["id"]))["memberships"][0]
    assert history["plan_id"] is None
    assert (history["plan_name"], history["amount"]) == ("Monthly", "5000.00")


async def test_saving_a_location_sets_the_gyms_time_zone(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id = await complete_profile(owner, storage)
    location = {
        "address_line": "Acacia Avenue",
        "neighbourhood": "Kololo",
        "city": "Kampala",
        "country_code": "ug",
        "latitude": "0.3376",
        "longitude": "32.5940",
    }

    response = await owner.call("PATCH", f"/gyms/{gym_id}/location", json=location)
    assert response.status_code == 200, response.json()
    assert response.json()["data"]["gym"]["timezone"] == "Africa/Kampala"

    # DR Congo has two time zones, so the gym keeps the one it has.
    location |= {"city": "Kinshasa", "country_code": "CD"}
    response = await owner.call("PATCH", f"/gyms/{gym_id}/location", json=location)
    assert response.json()["data"]["gym"]["timezone"] == "Africa/Kampala"
