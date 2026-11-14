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


@pytest.mark.parametrize("mobile", ["0712345678", "0110123456", "+254111234567"])
def test_require_mobile_accepts_kenyan_mobile_numbers(mobile: str) -> None:
    assert normalize_phone_number(
        mobile, default_region="KE", require_mobile=True
    ).startswith("+254")


@pytest.mark.parametrize("landline", ["0202222222", "+254412222222"])
def test_require_mobile_rejects_landlines(landline: str) -> None:
    with pytest.raises(InvalidPhoneNumberError, match="landline"):
        normalize_phone_number(landline, default_region="KE", require_mobile=True)


def test_landlines_remain_valid_where_mobile_is_not_required() -> None:
    assert normalize_phone_number("0202222222", default_region="KE") == "+254202222222"
