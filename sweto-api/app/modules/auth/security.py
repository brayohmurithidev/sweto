import hashlib
import hmac
import secrets
from uuid import UUID

from pwdlib import PasswordHash

from app.modules.auth.exceptions import PasswordPolicyViolationError

password_hash = PasswordHash.recommended()


def normalize_email(email: str) -> str:
    """Normalize an email identity for storage and lookup."""

    return email.strip().lower()


def hash_password(password: str) -> str:
    """Hash a human password with the configured Argon2 hasher."""

    return password_hash.hash(password)


def verify_password(password: str, password_hash_value: str) -> bool:
    """Verify a human password without exposing hash parsing errors."""

    try:
        return password_hash.verify(password, password_hash_value)
    except (TypeError, ValueError):
        return False


def password_needs_rehash(password_hash_value: str) -> bool:
    """Return whether a stored password hash uses outdated parameters."""

    try:
        return password_hash.current_hasher.check_needs_rehash(password_hash_value)
    except (TypeError, ValueError):
        return True


def validate_password_policy(password: str) -> None:
    """Enforce the shared policy for human passwords."""

    if len(password) < 12 or len(password) > 128 or not password.strip():
        raise PasswordPolicyViolationError(
            "The password must be between 12 and 128 non-blank characters."
        )


def generate_numeric_otp(length: int) -> str:
    """Generate a cryptographically secure fixed-length numeric OTP."""

    if length <= 0:
        raise ValueError("OTP length must be greater than zero.")

    upper_bound = 10**length
    number = secrets.randbelow(upper_bound)

    return f"{number:0{length}d}"


def hash_otp(
    *,
    challenge_id: UUID,
    phone_number: str,
    otp_code: str,
    secret: str,
) -> str:
    """Create an HMAC hash for an OTP challenge."""

    message = (f"{challenge_id}:{phone_number}:{otp_code}").encode()

    return hmac.new(
        secret.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()


def verify_otp_hash(
    *,
    challenge_id: UUID,
    phone_number: str,
    otp_code: str,
    secret: str,
    expected_hash: str,
) -> bool:
    """Safely compare a submitted OTP with its stored hash."""

    calculated_hash = hash_otp(
        challenge_id=challenge_id,
        phone_number=phone_number,
        otp_code=otp_code,
        secret=secret,
    )

    return hmac.compare_digest(
        calculated_hash,
        expected_hash,
    )
