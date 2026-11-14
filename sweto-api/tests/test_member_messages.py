"""Member SMS texts fit one GSM-7 segment."""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.members import messages

# GSM 03.38 basic set, without the escape table.
GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
LONG_GYM = "The Ultimate Strength And Conditioning Centre Westlands"


@pytest.mark.parametrize("gym_phone", ["+254722000000", None])
def test_every_member_text_fits_one_segment(gym_phone: str | None) -> None:
    texts = [
        messages.welcome(
            gym_name=LONG_GYM,
            gym_phone=gym_phone,
            code="HS47-CCDJ",
            paid_until=date(2026, 12, 31),
        ),
        messages.payment_receipt(
            gym_name=LONG_GYM,
            gym_phone=gym_phone,
            amount=Decimal("1234567.00"),
            currency="KES",
            paid_until=date(2026, 12, 31),
        ),
        messages.check_in_code(
            gym_name=LONG_GYM, gym_phone=gym_phone, code="HS47-CCDJ"
        ),
        messages.expiry_reminder(
            gym_name=LONG_GYM,
            gym_phone=gym_phone,
            ends_on=date(2026, 9, 30),
            today=date(2026, 9, 27),
        ),
    ]
    for text in texts:
        assert len(text) <= messages.SMS_LIMIT, (len(text), text)
        assert set(text) <= GSM7, text
        assert "STOP" not in text


def test_long_gym_names_are_shortened() -> None:
    text = messages.check_in_code(gym_name=LONG_GYM, gym_phone=None, code="HS47-CCDJ")
    assert text.startswith("The Ultimate Strength A.: ")
