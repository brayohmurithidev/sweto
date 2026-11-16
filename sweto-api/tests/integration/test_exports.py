"""CSV exports of a month's payments and the member list."""

import csv
import io

import pytest

from tests.integration.conftest import IntegrationAPI
from tests.integration.test_gym_members import add_member, gym_with_plans, pay_cash
from tests.integration.test_gym_owner_journey import FakeStorage, sign_in_owner
from tests.integration.test_gym_staff import hire

pytestmark = pytest.mark.usefixtures("pinned_clock")


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


def rows(body: bytes) -> list[list[str]]:
    text = body.decode("utf-8")
    assert text.startswith("﻿")  # Excel reads accents with a BOM
    return list(csv.reader(io.StringIO(text.removeprefix("﻿"))))


async def test_the_owner_exports_a_months_payments(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add_member(owner, gym_id, "Achieng Otieno", "0711000001")
    paid = await pay_cash(owner, gym_id, member["id"], plan_id=plans["Monthly"])
    assert paid.status_code == 201, paid.json()

    response = await owner.call("GET", f"/gyms/{gym_id}/exports/payments.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'payments-2026-11.csv"' in response.headers["content-disposition"]
    header, *data = rows(response.content)
    assert header[:6] == ["Date", "Member", "Plan", "Method", "Status", "Amount"]
    assert len(data) == 1
    assert data[0][1:7] == [
        "Achieng Otieno",
        "Monthly",
        "Cash",
        "Completed",
        "5000.00",
        "KES",
    ]

    # Another month has nothing in it.
    other = await owner.call(
        "GET", f"/gyms/{gym_id}/exports/payments.csv", params={"month": "2026-10"}
    )
    assert rows(other.content)[1:] == []


async def test_the_member_list_exports_with_phones_and_is_formula_safe(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    await add_member(owner, gym_id, "Achieng Otieno", "0711000001")
    sneaky = await add_member(owner, gym_id, "=HYPERLINK(1)", "0711000002")
    await owner.call("POST", f"/gyms/{gym_id}/members/{sneaky['id']}/archive")

    response = await owner.call("GET", f"/gyms/{gym_id}/exports/members.csv")

    assert response.status_code == 200
    header, *data = rows(response.content)
    assert header[:4] == ["Name", "Phone", "Archived", "Standing"]
    assert data[0][:4] == ["Achieng Otieno", "+254711000001", "", "No membership"]
    # Archived come last, and a name can't run as a spreadsheet formula.
    assert data[1][:3] == ["'=HYPERLINK(1)", "+254711000002", "Archived"]


async def test_only_owner_and_manager_export(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    receptionist, _ = await hire(api, owner, gym_id, "receptionist", "0744000000")
    manager, _ = await hire(api, owner, gym_id, "manager", "0766000000")

    for path in ("payments.csv", "members.csv"):
        url = f"/gyms/{gym_id}/exports/{path}"
        assert (await receptionist.call("GET", url)).status_code == 403
        assert (await manager.call("GET", url)).status_code == 200
    other = await sign_in_owner(api, phone="0733000000")
    url = f"/gyms/{gym_id}/exports/members.csv"
    assert (await other.call("GET", url)).status_code == 403
    assert (await api.client.get(f"/api/v1{url}")).status_code == 401
