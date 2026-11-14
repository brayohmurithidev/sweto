"""Member check-in codes.

8 characters from an alphabet without look-alikes (no 0/O, 1/I/L), shown as
``ABCD-EFGH``. Only a keyed hash is stored, so the database can find a member
by code without ever holding the code.
"""

import hashlib
import hmac
import re
import secrets

CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 8
QR_PREFIX = "sweto:checkin:"

_STRIP = re.compile(r"[\s\-]")


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def display_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


def qr_payload(code: str) -> str:
    """What the member's QR encodes: the code, nothing about the person."""

    return f"{QR_PREFIX}{code}"


def normalize_code(raw: str) -> str | None:
    """A typed or scanned code in canonical form, or None if it can't be one."""

    value = raw.strip()
    if value.lower().startswith(QR_PREFIX):
        value = value[len(QR_PREFIX) :]
    value = _STRIP.sub("", value).upper()
    if len(value) != CODE_LENGTH or any(c not in CODE_ALPHABET for c in value):
        return None
    return value


def hash_code(code: str, *, secret: str) -> str:
    return hmac.new(
        secret.encode(), f"check-in-code:{code}".encode(), hashlib.sha256
    ).hexdigest()
