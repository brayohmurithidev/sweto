"""CSV exports for the gym's own records: a month's payments and the member
list. They open in Excel or Google Sheets."""

import csv
import io
import re
from datetime import date
from uuid import UUID
from zoneinfo import ZoneInfo

from app.modules.gyms.permissions import GymPermission
from app.modules.members.enums import GymMemberStatus, PaymentMethod
from app.modules.members.finance_service import FinanceService
from app.modules.members.service import GymMemberService

PAGE = 200
_NUMBER = re.compile(r"[+-]?\d+(\.\d+)?")
_STANDING = {
    "active": "Active",
    "expiring": "Expiring",
    "expired": "Expired",
    "no_membership": "No membership",
    "upcoming": "Starts later",
}


def _cell(value: object) -> str:
    """A cell value Excel won't run as a formula (names are typed by people)."""

    text = "" if value is None else str(value)
    if _NUMBER.fullmatch(text):  # +254…, -500.00: data, not formulas
        return text
    return "'" + text if text[:1] in {"=", "+", "-", "@", "\t", "\r"} else text


def _csv(header: list[str], rows: list[list[object]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    writer.writerows([[_cell(v) for v in row] for row in rows])
    # A byte-order mark so Excel reads names with accents correctly.
    return "﻿" + out.getvalue()


class GymExports:
    def __init__(self, *, members: GymMemberService, finance: FinanceService) -> None:
        self.members = members
        self.finance = finance

    async def payments_csv(
        self, *, user_id: UUID, gym_id: UUID, month: date | None
    ) -> tuple[str, str]:
        """(file name, CSV) of every payment in the month, newest first."""

        gym = await self.members._gym_for(
            user_id=user_id, gym_id=gym_id, permission=GymPermission.VIEW_FINANCE
        )
        zone = ZoneInfo(gym.timezone)
        rows: list[list[object]] = []
        offset = 0
        while True:
            page = await self.finance.transactions(
                user_id=user_id,
                gym_id=gym_id,
                month=month,
                method=None,
                status=None,
                limit=PAGE,
                offset=offset,
            )
            for t in page.transactions:
                rows.append(
                    [
                        t.at.astimezone(zone).strftime("%Y-%m-%d %H:%M"),
                        t.member_name,
                        t.plan_name,
                        "M-Pesa" if t.method == PaymentMethod.MPESA else "Cash",
                        t.status.value.capitalize(),
                        f"{t.amount:.2f}",
                        t.currency,
                        t.receipt or "",
                        t.recorded_by_name or "",
                    ]
                )
            offset += PAGE
            if offset >= page.total:
                break
        label = (month or self.members._today(gym)).strftime("%Y-%m")
        return (
            f"{_slug(gym.name)}-payments-{label}.csv",
            _csv(
                [
                    "Date",
                    "Member",
                    "Plan",
                    "Method",
                    "Status",
                    "Amount",
                    "Currency",
                    "M-Pesa receipt",
                    "Recorded by",
                ],
                rows,
            ),
        )

    async def members_csv(self, *, user_id: UUID, gym_id: UUID) -> tuple[str, str]:
        """(file name, CSV) of every member, active first, then archived."""

        gym = await self.members._gym_for(
            user_id=user_id, gym_id=gym_id, permission=GymPermission.EXPORT_MEMBERS
        )
        rows: list[list[object]] = []
        for status in (GymMemberStatus.ACTIVE, GymMemberStatus.ARCHIVED):
            offset = 0
            while True:
                page = await self.members.list_members(
                    user_id=user_id,
                    gym_id=gym_id,
                    status=status,
                    search=None,
                    standing=None,
                    limit=100,
                    offset=offset,
                )
                for m in page.members:
                    rows.append(
                        [
                            m.full_name,
                            m.phone_number,
                            "Archived" if status == GymMemberStatus.ARCHIVED else "",
                            _STANDING.get(m.standing.value, m.standing.value),
                            m.starts_on or "",
                            m.paid_until or "",
                            "Yes" if m.sms_enabled else "No",
                            m.created_at.date(),
                        ]
                    )
                offset += 100
                if offset >= page.total:
                    break
        today = self.members._today(gym)
        return (
            f"{_slug(gym.name)}-members-{today:%Y-%m-%d}.csv",
            _csv(
                [
                    "Name",
                    "Phone",
                    "Archived",
                    "Standing",
                    "Starts on",
                    "Paid until",
                    "SMS",
                    "Added on",
                ],
                rows,
            ),
        )


def _slug(name: str) -> str:
    cleaned = "".join(c.lower() if c.isalnum() else "-" for c in name)
    return "-".join(part for part in cleaned.split("-") if part) or "gym"
