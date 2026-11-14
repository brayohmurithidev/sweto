"""Check-in codes and check-ins at the door (MVP build order, PR 4).

The clock is pinned (see test_gym_members); gyms are on Nairobi time (UTC+3).
"""

from typing import Any

import pytest

from tests.integration.conftest import IntegrationAPI, PinnedClock
from tests.integration.test_gym_members import add_member, gym_with_plans, pay_cash
from tests.integration.test_gym_owner_journey import FakeStorage, Owner, sign_in_owner

pytestmark = pytest.mark.usefixtures("pinned_clock")


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


async def issue_code(owner: Owner, gym_id: str, member_id: str) -> dict[str, Any]:
    response = await owner.call(
        "POST", f"/gyms/{gym_id}/members/{member_id}/check-in-code"
    )
    assert response.status_code == 201, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


async def check_in(owner: Owner, gym_id: str, code: str) -> dict[str, Any]:
    response = await owner.call(
        "POST", f"/gyms/{gym_id}/check-ins", json={"code": code}
    )
    assert response.status_code == 200, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


async def paid_member(
    owner: Owner, gym_id: str, plan_id: str, phone: str = "0711000001"
) -> tuple[dict[str, Any], str]:
    member = await add_member(owner, gym_id, phone=phone)
    assert (
        await pay_cash(owner, gym_id, member["id"], plan_id=plan_id)
    ).status_code == 201
    return member, (await issue_code(owner, gym_id, member["id"]))["code"]


async def test_a_paid_member_checks_in_by_typed_code_or_qr(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add_member(owner, gym_id)
    await pay_cash(owner, gym_id, member["id"], plan_id=plans["Monthly"])

    issued = await issue_code(owner, gym_id, member["id"])
    code = issued["code"]
    assert len(code) == 9 and code[4] == "-"
    assert issued["qr_payload"] == f"sweto:checkin:{code.replace('-', '')}"
    assert "Otieno" not in issued["qr_payload"]

    first = await check_in(owner, gym_id, code.lower().replace("-", " "))
    assert first["result"] == "allowed" and first["allowed"] is True
    assert first["already_checked_in_today"] is False
    assert first["member"]["full_name"] == "Achieng Otieno"
    assert first["member"]["paid_until"] == "2026-12-13"
    assert first["membership"]["plan_name"] == "Monthly"
    assert first["message"] == "Welcome, Achieng Otieno."

    # Back the same day: let in, flagged, and not a second visit.
    again = await check_in(owner, gym_id, issued["qr_payload"])
    assert again["result"] == "allowed"
    assert again["already_checked_in_today"] is True

    day = (await owner.call("GET", f"/gyms/{gym_id}/check-ins")).json()["data"]
    assert (day["date"], day["visits"], day["refused"]) == ("2026-11-14", 1, 0)
    assert [e["already_checked_in_today"] for e in day["check_ins"]] == [True, False]

    detail = (await owner.call("GET", f"/gyms/{gym_id}/members/{member['id']}")).json()
    assert detail["data"]["member"]["has_check_in_code"] is True


async def test_a_new_code_replaces_the_old_one(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member, old_code = await paid_member(owner, gym_id, plans["Monthly"])

    new_code = (await issue_code(owner, gym_id, member["id"]))["code"]

    assert new_code != old_code
    assert (await check_in(owner, gym_id, old_code))["result"] == "unknown_code"
    assert (await check_in(owner, gym_id, new_code))["result"] == "allowed"


async def test_refusals_say_why_and_are_logged(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    weekly, weekly_code = await paid_member(owner, gym_id, plans["Weekly"])  # to 20 Nov
    unpaid = await add_member(owner, gym_id, "Never Paid", "0711000002")
    unpaid_code = (await issue_code(owner, gym_id, unpaid["id"]))["code"]
    archived, archived_code = await paid_member(
        owner, gym_id, plans["Monthly"], phone="0711000003"
    )
    await owner.call("POST", f"/gyms/{gym_id}/members/{archived['id']}/archive")

    unpaid_result = await check_in(owner, gym_id, unpaid_code)
    assert unpaid_result["result"] == "no_membership"
    assert unpaid_result["allowed"] is False
    assert (await check_in(owner, gym_id, archived_code))["result"] == "archived"
    unknown = await check_in(owner, gym_id, "ZZZZ-ZZZZ")
    assert (unknown["result"], unknown["member"]) == ("unknown_code", None)
    assert (await check_in(owner, gym_id, "not a code"))["result"] == "unknown_code"

    pinned_clock.set("2026-11-21T06:00:00+00:00")
    expired = await check_in(owner, gym_id, weekly_code)
    assert expired["result"] == "expired"
    assert expired["member"]["paid_until"] == "2026-11-20"
    assert expired["message"] == "Achieng Otieno's membership ended on 20 Nov 2026."

    day = (await owner.call("GET", f"/gyms/{gym_id}/check-ins")).json()["data"]
    assert (day["visits"], day["refused"]) == (0, 1)
    log = await api.sql(
        "SELECT result, member_id IS NULL FROM gym_check_ins ORDER BY checked_in_at"
    )
    assert sorted(log) == sorted(
        [
            ("no_membership", False),
            ("archived", False),
            ("unknown_code", True),
            ("unknown_code", True),
            ("expired", False),
        ]
    )


async def test_a_membership_that_has_not_started_is_refused(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    member = await add_member(owner, gym_id)
    code = (await issue_code(owner, gym_id, member["id"]))["code"]
    await api.sql(
        "INSERT INTO gym_memberships (id, gym_id, member_id, plan_name, amount, "
        "currency, billing_period, starts_on, ends_on, status) VALUES "
        "(gen_random_uuid(), :gym_id, :member_id, 'Monthly', 5000, 'KES', "
        "'monthly', '2026-11-20', '2026-12-19', 'active')",
        gym_id=gym_id,
        member_id=member["id"],
    )

    result = await check_in(owner, gym_id, code)

    assert result["result"] == "not_started"
    assert result["message"] == "Achieng Otieno's membership starts on 20 Nov 2026."


async def test_visit_limits_count_days_not_repeat_scans(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    pricing = await owner.call(
        "PUT",
        f"/gyms/{gym_id}/pricing",
        json={
            "day_passes": [{"name": "Day Pass", "amount": "500.00"}],
            "membership_plans": [
                {
                    "name": "Two Visits",
                    "amount": "800.00",
                    "billing_period": "monthly",
                    "visit_limit": 2,
                }
            ],
        },
    )
    plan_id = pricing.json()["data"]["membership_plans"][0]["id"]
    _, code = await paid_member(owner, gym_id, plan_id)

    assert (await check_in(owner, gym_id, code))["membership"]["visits_used"] == 1
    assert (await check_in(owner, gym_id, code))["already_checked_in_today"] is True
    pinned_clock.set("2026-11-15T06:00:00+00:00")
    second = await check_in(owner, gym_id, code)
    assert (second["result"], second["membership"]["visits_used"]) == ("allowed", 2)

    pinned_clock.set("2026-11-16T06:00:00+00:00")
    third = await check_in(owner, gym_id, code)
    assert third["result"] == "visit_limit_reached"
    assert third["message"] == "Achieng Otieno has used all 2 visits on this plan."


async def test_days_and_expiry_follow_the_gyms_midnight(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    _, code = await paid_member(owner, gym_id, plans["Weekly"])  # 14 to 20 Nov

    # 23:59:59 on 20 Nov in Nairobi: last moment of the last day.
    pinned_clock.set("2026-11-20T20:59:59+00:00")
    assert (await check_in(owner, gym_id, code))["result"] == "allowed"
    # Midnight in Nairobi (still 20 Nov in UTC): a new day, and expired.
    pinned_clock.set("2026-11-20T21:00:00+00:00")
    assert (await check_in(owner, gym_id, code))["result"] == "expired"

    day = await owner.call(
        "GET", f"/gyms/{gym_id}/check-ins", params={"date": "2026-11-20"}
    )
    assert day.json()["data"]["visits"] == 1
    next_day = (await owner.call("GET", f"/gyms/{gym_id}/check-ins")).json()["data"]
    assert (next_day["date"], next_day["refused"]) == ("2026-11-21", 1)


async def test_codes_only_work_at_their_own_gym(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member, code = await paid_member(owner, gym_id, plans["Monthly"])
    other = await sign_in_owner(api, phone="0733000000")
    other_gym_id, _ = await gym_with_plans(other, storage)

    assert (await check_in(other, other_gym_id, code))["result"] == "unknown_code"
    response = await other.call(
        "POST", f"/gyms/{gym_id}/check-ins", json={"code": code}
    )
    assert response.status_code == 403
    response = await other.call(
        "POST", f"/gyms/{other_gym_id}/members/{member['id']}/check-in-code"
    )
    assert response.status_code == 404
    response = await other.call("GET", f"/gyms/{gym_id}/check-ins")
    assert response.status_code == 403


async def test_door_staff_check_in_but_only_managers_issue_codes(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member, code = await paid_member(owner, gym_id, plans["Monthly"])
    receptionist = await sign_in_owner(api, phone="0744000000")
    await api.sql(
        "INSERT INTO gym_staff (id, gym_id, user_id, role, status, is_primary_owner) "
        "SELECT gen_random_uuid(), :gym_id, id, 'receptionist', 'active', false "
        "FROM users WHERE phone_number = '+254744000000'",
        gym_id=gym_id,
    )

    assert (await check_in(receptionist, gym_id, code))["result"] == "allowed"
    response = await receptionist.call(
        "POST", f"/gyms/{gym_id}/members/{member['id']}/check-in-code"
    )
    assert response.status_code == 403
    response = await api.client.post(
        f"/api/v1/gyms/{gym_id}/check-ins", json={"code": code}
    )
    assert response.status_code == 401


async def test_check_in_attempts_are_rate_limited_per_gym(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    _, code = await paid_member(owner, gym_id, plans["Monthly"])
    api.settings.check_in_attempt_limit = 3

    for _ in range(3):
        await check_in(owner, gym_id, "ZZZZ-ZZZZ")
    # Even a valid code waits: guessing must not be able to outrun the limit.
    response = await owner.call(
        "POST", f"/gyms/{gym_id}/check-ins", json={"code": code}
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "CHECK_IN_RATE_LIMITED"
    assert int(response.headers["Retry-After"]) > 0
