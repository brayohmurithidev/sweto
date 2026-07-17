from uuid import uuid4

from app.modules.auth.security import (
    generate_numeric_otp,
    hash_otp,
    verify_otp_hash,
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
