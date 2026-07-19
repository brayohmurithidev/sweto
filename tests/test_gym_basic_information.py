import pytest
from pydantic import ValidationError

from app.modules.gyms.schemas import UpdateGymBasicInformationRequest


def test_basic_information_patch_supports_partial_updates() -> None:
    payload = UpdateGymBasicInformationRequest(phone_number="+254712345678")
    assert payload.phone_number == "+254712345678"
    assert payload.name is None


def test_basic_information_patch_rejects_empty_body() -> None:
    with pytest.raises(ValidationError):
        UpdateGymBasicInformationRequest()


def test_basic_information_patch_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        UpdateGymBasicInformationRequest(name="   ")


def test_basic_information_patch_preserves_explicit_clears() -> None:
    payload = UpdateGymBasicInformationRequest(
        phone_number=None,
        email=None,
        description=None,
    )
    assert payload.model_fields_set == {"phone_number", "email", "description"}
