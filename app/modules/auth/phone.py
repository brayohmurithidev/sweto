import phonenumbers
from phonenumbers import PhoneNumberFormat

from app.modules.auth.exceptions import InvalidPhoneNumberError


def normalize_phone_number(
    phone_number: str,
    *,
    default_region: str,
) -> str:
    """
    Normalize a phone number to E.164 format.

    Examples for the KE region:
        0712345678    -> +254712345678
        712345678     -> +254712345678
        +254712345678 -> +254712345678
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

    return phonenumbers.format_number(
        parsed_number,
        PhoneNumberFormat.E164,
    )
