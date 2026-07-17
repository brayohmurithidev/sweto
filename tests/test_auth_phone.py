import pytest

from app.modules.auth.exceptions import InvalidPhoneNumberError
from app.modules.auth.phone import normalize_phone_number


@pytest.mark.parametrize(
    ("raw_number", "expected"),
    [
        ("0712345678", "+254712345678"),
        ("712345678", "+254712345678"),
        ("+254712345678", "+254712345678"),
    ],
)
def test_normalize_kenyan_phone_number(
    raw_number: str,
    expected: str,
) -> None:
    assert (
        normalize_phone_number(
            raw_number,
            default_region="KE",
        )
        == expected
    )


def test_normalize_phone_number_rejects_invalid_number() -> None:
    with pytest.raises(InvalidPhoneNumberError):
        normalize_phone_number(
            "123",
            default_region="KE",
        )
