"""Gym staff: the owner adds people by phone, each role sees only its share."""

from typing import Any

import pytest

from tests.integration.conftest import IntegrationAPI
from tests.integration.test_gym_members import add_member, gym_with_plans, pay_cash
from tests.integration.test_gym_owner_journey import FakeStorage, Owner, sign_in_owner

pytestmark = pytest.mark.usefixtures("pinned_clock")


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


async def sign_in(api: IntegrationAPI, phone: str) -> tuple[Owner, str]:
    """Plain phone sign-in, as staff do: no account type is chosen."""

    requested = await api.client.post(
        "/api/v1/auth/request-otp", json={"phone_number": phone}
    )
    assert requested.status_code == 201, requested.json()
    verified = await api.client.post(
        "/api/v1/auth/verify-otp",
        json={
            "challenge_id": requested.json()["data"]["challenge_id"],
            "code": api.sms.last_code(),
        },
    )
    assert verified.status_code == 200, verified.json()
    tokens = verified.json()["data"]["tokens"]
    return Owner(api, tokens["access_token"]), tokens["refresh_token"]


async def add_staff(
    owner: Owner, gym_id: str, role: str, phone: str, name: str = "Wanjiku Kamau"
) -> Any:
    return await owner.call(
        "POST",
        f"/gyms/{gym_id}/staff",
        json={"full_name": name, "phone_number": phone, "role": role},
    )


async def hire(
    api: IntegrationAPI, owner: Owner, gym_id: str, role: str, phone: str
) -> tuple[Owner, dict[str, Any]]:
    response = await add_staff(owner, gym_id, role, phone)
    assert response.status_code == 201, response.json()
    staff, _ = await sign_in(api, phone)
    return staff, response.json()["data"]["staff"]


async def test_added_staff_get_an_invite_and_land_in_the_gym(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)

    response = await add_staff(owner, gym_id, "receptionist", "0744000000")
    assert response.status_code == 201, response.json()
    added = response.json()["data"]
    assert added["invite_sms"] == "sent"
    assert added["staff"]["role"] == "receptionist"
    assert added["staff"]["full_name"] == "Wanjiku Kamau"
    assert added["staff"]["has_signed_in"] is False
    phone, text = api.sms.texts[-1]
    assert phone == "+254744000000"
    assert "as a receptionist" in text

    listed = (await owner.call("GET", f"/gyms/{gym_id}/staff")).json()["data"]
    assert [s["role"] for s in listed["staff"]] == ["owner", "receptionist"]

    staff, _ = await sign_in(api, "0744000000")
    onboarding = (await staff.call("GET", "/account/onboarding")).json()["data"]
    assert onboarding["next_step"] == "gym_staff"
    current = (await staff.call("GET", "/gyms/current")).json()["data"]
    assert current["id"] == gym_id
    access = (await staff.call("GET", f"/gyms/{gym_id}/staff/me")).json()["data"]
    assert access["role"] == "receptionist"
    assert "take_payments" in access["permissions"]
    assert "view_finance" not in access["permissions"]

    listed = (await owner.call("GET", f"/gyms/{gym_id}/staff")).json()["data"]
    assert listed["staff"][1]["has_signed_in"] is True

    # Working at a gym rules out registering one.
    response = await staff.call("POST", "/gyms", json={"name": "Side Hustle Gym"})
    assert response.status_code == 409


async def test_each_role_gets_only_its_share(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add_member(owner, gym_id)
    receptionist, _ = await hire(api, owner, gym_id, "receptionist", "0744000000")
    trainer, _ = await hire(api, owner, gym_id, "trainer", "0755000000")
    manager, _ = await hire(api, owner, gym_id, "manager", "0766000000")

    # Front desk: members and payments, but not money totals or settings.
    new = await receptionist.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={"full_name": "Otieno Front", "phone_number": "0711000002"},
    )
    assert new.status_code == 201
    paid = await pay_cash(receptionist, gym_id, member["id"], plan_id=plans["Monthly"])
    assert paid.status_code == 201, paid.json()
    for method, path, body in [
        ("GET", f"/gyms/{gym_id}/finance", None),
        ("GET", f"/gyms/{gym_id}/staff", None),
        ("POST", f"/gyms/{gym_id}/members/{member['id']}/archive", None),
        ("PATCH", f"/gyms/{gym_id}/basic-information", {"name": "Renamed"}),
    ]:
        response = await receptionist.call(method, path, json=body)
        assert response.status_code == 403, (method, path)
    dashboard = await receptionist.call("GET", f"/gyms/{gym_id}/dashboard")
    assert dashboard.json()["data"]["revenue"] is None
    assert (await receptionist.call("GET", f"/gyms/{gym_id}/pricing")).status_code == (
        200
    )

    # Trainers: look members up and check them in, nothing more.
    assert (await trainer.call("GET", f"/gyms/{gym_id}/members")).status_code == 200
    response = await trainer.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={"full_name": "Not Allowed", "phone_number": "0711000003"},
    )
    assert response.status_code == 403
    response = await pay_cash(trainer, gym_id, member["id"], plan_id=plans["Monthly"])
    assert response.status_code == 403

    # Managers run the gym but not its staff, till or verification.
    assert (await manager.call("GET", f"/gyms/{gym_id}/finance")).status_code == 200
    archived = await manager.call(
        "POST", f"/gyms/{gym_id}/members/{member['id']}/archive"
    )
    assert archived.status_code == 200
    assert (await manager.call("GET", f"/gyms/{gym_id}/staff")).status_code == 403
    response = await manager.call(
        "PUT",
        f"/gyms/{gym_id}/mpesa-account",
        json={"account_type": "paybill", "shortcode": "174379", "passkey": "x" * 20},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "GYM_ACCESS_DENIED"


async def test_one_gym_per_person_and_the_owner_stays_owner(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    other = await sign_in_owner(api, phone="0733000000")
    other_gym_id, _ = await gym_with_plans(other, storage)
    _, receptionist = await hire(api, owner, gym_id, "receptionist", "0744000000")

    again = await add_staff(owner, gym_id, "trainer", "0744000000")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "STAFF_PHONE_TAKEN"
    elsewhere = await add_staff(other, other_gym_id, "trainer", "0744000000")
    assert elsewhere.status_code == 409
    assert "another gym" in elsewhere.json()["error"]["message"]
    # Another gym's owner cannot be hired either.
    assert (await add_staff(owner, gym_id, "manager", "0733000000")).status_code == 409

    assert (await add_staff(owner, gym_id, "owner", "0777000000")).status_code == 422
    staff = (await owner.call("GET", f"/gyms/{gym_id}/staff")).json()["data"]
    owner_row = staff["staff"][0]
    response = await owner.call(
        "PATCH", f"/gyms/{gym_id}/staff/{owner_row['id']}", json={"role": "trainer"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "STAFF_CHANGE_NOT_ALLOWED"

    promoted = await owner.call(
        "PATCH",
        f"/gyms/{gym_id}/staff/{receptionist['id']}",
        json={"role": "manager"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["data"]["role"] == "manager"


async def test_suspending_or_removing_cuts_access_at_once(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    await add_staff(owner, gym_id, "receptionist", "0744000000")
    staff, refresh_token = await sign_in(api, "0744000000")
    row = (await owner.call("GET", f"/gyms/{gym_id}/staff")).json()["data"]["staff"][1]
    members = f"/gyms/{gym_id}/members"
    assert (await staff.call("GET", members)).status_code == 200

    suspended = await owner.call(
        "PATCH", f"/gyms/{gym_id}/staff/{row['id']}", json={"status": "suspended"}
    )
    assert suspended.status_code == 200
    # Suspension signs them out everywhere at once.
    assert (await staff.call("GET", members)).status_code == 401
    refreshed = await api.client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token, "platform": "flutter"},
    )
    assert refreshed.status_code == 401
    staff, _ = await sign_in(api, "0744000000")
    onboarding = (await staff.call("GET", "/account/onboarding")).json()["data"]
    assert onboarding["next_step"] == "staff_suspended"

    await owner.call(
        "PATCH", f"/gyms/{gym_id}/staff/{row['id']}", json={"status": "active"}
    )
    assert (await staff.call("GET", members)).status_code == 200

    removed = await owner.call("DELETE", f"/gyms/{gym_id}/staff/{row['id']}")
    assert removed.status_code == 204
    assert (await staff.call("GET", members)).status_code == 401
    listed = (await owner.call("GET", f"/gyms/{gym_id}/staff")).json()["data"]
    assert [s["role"] for s in listed["staff"]] == ["owner"]

    # Added back later, they return on their old record with the new role.
    back = await add_staff(owner, gym_id, "trainer", "0744000000")
    assert back.status_code == 201
    assert back.json()["data"]["staff"]["id"] == row["id"]
    assert back.json()["data"]["staff"]["role"] == "trainer"


async def test_a_failed_invite_sms_still_adds_them(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    from app.integrations.sms.base import SMSDeliveryError

    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    api.sms.failure = SMSDeliveryError("provider down")

    response = await add_staff(owner, gym_id, "trainer", "0744000000")

    assert response.status_code == 201
    assert response.json()["data"]["invite_sms"] == "failed"
