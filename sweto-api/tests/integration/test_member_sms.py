"""SMS to members: consent, welcome, receipts, codes, reminders (PR 5)."""

import os
import re
import subprocess
import sys
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.integrations.sms.base import SMSDeliveryError
from app.jobs.membership_reminders import send_due_reminders
from tests.integration.conftest import IntegrationAPI, PinnedClock
from tests.integration.test_check_ins import check_in
from tests.integration.test_gym_members import gym_with_plans, pay_cash
from tests.integration.test_gym_owner_journey import FakeStorage, Owner, sign_in_owner

pytestmark = pytest.mark.usefixtures("pinned_clock")

CODE = re.compile(r"[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}")


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    fake = FakeStorage()
    monkeypatch.setattr("app.modules.gyms.router.S3Storage", lambda _settings: fake)
    return fake


async def add(
    owner: Owner, gym_id: str, *, consent: bool, phone: str = "0711000001"
) -> dict[str, Any]:
    response = await owner.call(
        "POST",
        f"/gyms/{gym_id}/members",
        json={
            "full_name": "Achieng Otieno",
            "phone_number": phone,
            "sms_consent": consent,
        },
    )
    assert response.status_code == 201, response.json()
    data: dict[str, Any] = response.json()["data"]
    return data


def texts_to(api: IntegrationAPI, phone: str) -> list[str]:
    return [message for to, message in api.sms.texts if to == phone]


async def test_no_consent_no_sms(api: IntegrationAPI, storage: FakeStorage) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add(owner, gym_id, consent=False)
    assert member["sms_enabled"] is False

    paid = await pay_cash(owner, gym_id, member["id"], plan_id=plans["Monthly"])

    assert paid.status_code == 201
    assert paid.json()["data"]["sms"] is None
    assert api.sms.texts == []


async def test_first_payment_welcomes_with_a_working_code_then_receipts(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add(owner, gym_id, consent=True)
    assert member["sms_enabled"] is True
    assert member["sms_consent_recorded_at"] is not None

    first = await pay_cash(owner, gym_id, member["id"], plan_id=plans["Monthly"])
    assert first.json()["data"]["sms"] == "sent"
    [welcome] = texts_to(api, "+254711000001")
    assert welcome.startswith("Welcome to FlexFit Westlands! Check-in code: ")
    assert "Paid until 13 Dec 2026." in welcome
    assert welcome.endswith("To stop SMS, tell the gym or call 0722000000.")
    assert "STOP" not in welcome
    code = CODE.search(welcome)
    assert code is not None
    assert (await check_in(owner, gym_id, code.group()))["result"] == "allowed"

    second = await pay_cash(
        owner, gym_id, member["id"], plan_id=plans["Monthly"], amount="4500"
    )
    assert second.json()["data"]["sms"] == "sent"
    receipt = texts_to(api, "+254711000001")[-1]
    assert receipt == (
        "FlexFit Westlands: received KES 4,500. Membership paid until 13 Jan "
        "2027. To stop SMS, tell the gym or call 0722000000."
    )
    # Only one welcome, ever.
    assert sum(t.startswith("Welcome") for t in texts_to(api, "+254711000001")) == 1


async def test_an_opted_out_member_gets_nothing_until_consent_is_recorded_again(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add(owner, gym_id, consent=True)
    base = f"/gyms/{gym_id}/members/{member['id']}"

    off = await owner.call("PUT", f"{base}/sms", json={"enabled": False})
    assert off.json()["data"]["sms_enabled"] is False
    assert off.json()["data"]["sms_opted_out_at"] is not None
    await pay_cash(owner, gym_id, member["id"], plan_id=plans["Monthly"])
    code = await owner.call("POST", f"{base}/check-in-code")
    assert code.json()["data"]["sms"] is None
    assert api.sms.texts == []

    on = await owner.call("PUT", f"{base}/sms", json={"enabled": True})
    assert on.json()["data"]["sms_enabled"] is True
    await pay_cash(owner, gym_id, member["id"], plan_id=plans["Monthly"])
    assert len(texts_to(api, "+254711000001")) == 1


async def test_a_new_code_is_texted_to_the_member(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, _ = await gym_with_plans(owner, storage)
    member = await add(owner, gym_id, consent=True)

    issued = await owner.call(
        "POST", f"/gyms/{gym_id}/members/{member['id']}/check-in-code"
    )

    assert issued.json()["data"]["sms"] == "sent"
    [message] = texts_to(api, "+254711000001")
    assert issued.json()["data"]["code"] in message
    assert "The old code no longer works." in message


async def test_a_provider_failure_never_breaks_the_payment(
    api: IntegrationAPI, storage: FakeStorage
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add(owner, gym_id, consent=True)
    api.sms.failure = SMSDeliveryError("provider_unavailable")

    paid = await pay_cash(owner, gym_id, member["id"], plan_id=plans["Monthly"])

    assert paid.status_code == 201, paid.json()
    assert paid.json()["data"]["sms"] == "failed"
    assert paid.json()["data"]["member"]["paid_until"] == "2026-12-13"
    rows = await api.sql("SELECT kind, status, error_reason FROM member_messages")
    assert rows == [("welcome", "failed", "provider_unavailable")]


async def test_reminders_go_three_days_before_and_on_the_day_once_each(
    api: IntegrationAPI, storage: FakeStorage, pinned_clock: PinnedClock
) -> None:
    owner = await sign_in_owner(api)
    gym_id, plans = await gym_with_plans(owner, storage)
    member = await add(owner, gym_id, consent=True)
    await pay_cash(owner, gym_id, member["id"], plan_id=plans["Weekly"])  # to 20 Nov
    renewed = await add(owner, gym_id, consent=True, phone="0711000002")
    await pay_cash(owner, gym_id, renewed["id"], plan_id=plans["Weekly"])
    await pay_cash(owner, gym_id, renewed["id"], plan_id=plans["Weekly"])  # to 27 Nov
    silent = await add(owner, gym_id, consent=False, phone="0711000003")
    await pay_cash(owner, gym_id, silent["id"], plan_id=plans["Weekly"])
    api.sms.texts.clear()
    factory = async_sessionmaker(
        bind=api.engine, class_=AsyncSession, expire_on_commit=False
    )

    async def run() -> dict[str, int]:
        outcomes = await send_due_reminders(
            session_factory=factory,
            sms=api.sms,
            settings=api.settings,
            clock=pinned_clock,
        )
        return dict(outcomes)

    # 23:59 on 16 Nov in Nairobi: 4 days to go, nothing due.
    pinned_clock.set("2026-11-16T20:59:00+00:00")
    assert await run() == {}
    # Midnight in Nairobi starts 17 Nov (UTC still says 16 Nov): 3 days to go.
    pinned_clock.set("2026-11-16T21:00:00+00:00")
    assert await run() == {"sent": 1}
    assert texts_to(api, "+254711000001") == [
        "FlexFit Westlands: your membership ends on 20 Nov 2026. Renew to keep "
        "checking in. To stop SMS, tell the gym or call 0722000000."
    ]
    # Running again the same day sends nothing new.
    assert await run() == {"already_sent": 1}

    pinned_clock.set("2026-11-20T06:00:00+00:00")
    assert await run() == {"sent": 1}
    assert texts_to(api, "+254711000001")[-1].startswith(
        "FlexFit Westlands: your membership ends today."
    )
    # The renewed member (paid to 27 Nov) and the one without consent got none.
    assert texts_to(api, "+254711000002") == []
    assert texts_to(api, "+254711000003") == []


def test_the_reminder_command_runs_on_its_own(migrated_database_url: str) -> None:
    """`python -m app.jobs.membership_reminders` works outside the API process."""
    result = subprocess.run(
        [sys.executable, "-m", "app.jobs.membership_reminders"],
        env={
            **os.environ,
            "DATABASE_URL": migrated_database_url,
            "SMS_PROVIDER": "console",
        },
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert "Membership reminders:" in result.stderr
