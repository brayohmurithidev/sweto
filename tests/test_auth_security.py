from uuid import uuid4

from app.modules.auth.security import (
    generate_numeric_otp,
    hash_otp,
    hash_password,
    password_needs_rehash,
    verify_otp_hash,
    verify_password,
)


def test_generate_numeric_otp_has_requested_length() -> None:
    otp = generate_numeric_otp(6)

    assert len(otp) == 6
    assert otp.isdigit()


def test_verify_otp_hash_accepts_correct_code() -> None:
    challenge_id = uuid4()

    hashed = hash_otp(
        challenge_id=challenge_id,
        phone_number="+254712345678",
        otp_code="123456",
        secret="test-secret",
    )

    assert verify_otp_hash(
        challenge_id=challenge_id,
        phone_number="+254712345678",
        otp_code="123456",
        secret="test-secret",
        expected_hash=hashed,
    )


def test_verify_otp_hash_rejects_wrong_code() -> None:
    challenge_id = uuid4()

    hashed = hash_otp(
        challenge_id=challenge_id,
        phone_number="+254712345678",
        otp_code="123456",
        secret="test-secret",
    )

    assert not verify_otp_hash(
        challenge_id=challenge_id,
        phone_number="+254712345678",
        otp_code="654321",
        secret="test-secret",
        expected_hash=hashed,
    )


def test_hash_password_uses_argon2_and_verifies() -> None:
    encoded = hash_password("a-secure-password")

    assert encoded.startswith("$argon2")
    assert verify_password("a-secure-password", encoded)
    assert not verify_password("the-wrong-password", encoded)


def test_password_rehash_detection_accepts_current_hash() -> None:
    encoded = hash_password("a-secure-password")

    assert not password_needs_rehash(encoded)


def test_password_rehash_detection_rejects_invalid_hash() -> None:
    assert password_needs_rehash("not-a-password-hash")
