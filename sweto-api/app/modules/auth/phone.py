import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneNumberType

from app.modules.auth.exceptions import InvalidPhoneNumberError

_SMS_CAPABLE_TYPES = frozenset(
    {
        PhoneNumberType.MOBILE,
        PhoneNumberType.FIXED_LINE_OR_MOBILE,
    }
)


def normalize_phone_number(
    phone_number: str,
    *,
    default_region: str,
    require_mobile: bool = False,
) -> str:
    """
    Normalize a phone number to E.164 format.

    Examples for the KE region:
        0712345678    -> +254712345678
        712345678     -> +254712345678
        +254712345678 -> +254712345678

    With ``require_mobile`` the number must be able to receive SMS, which
    rejects landlines before an OTP is generated for them.
    """

    cleaned_number = phone_number.strip()

    if not cleaned_number:
        raise InvalidPhoneNumberError("Phone number is required.")

    try:
        parsed_number = phonenumbers.parse(
            cleaned_number,
            default_region,
        )
    except phonenumbers.NumberParseException as exc:
        raise InvalidPhoneNumberError("Enter a valid phone number.") from exc

    if not phonenumbers.is_valid_number(parsed_number):
        raise InvalidPhoneNumberError("Enter a valid phone number.")

    if (
        require_mobile
        and phonenumbers.number_type(parsed_number) not in _SMS_CAPABLE_TYPES
    ):
        raise InvalidPhoneNumberError(
            "Enter a mobile number. Verification codes can't be sent to landlines."
        )

    return phonenumbers.format_number(
        parsed_number,
        PhoneNumberFormat.E164,
    )
