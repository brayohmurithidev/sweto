"""Encrypts each gym's M-Pesa passkey at rest (Fernet: AES + HMAC)."""

from cryptography.fernet import Fernet, InvalidToken


class MpesaCredentialsError(Exception):
    """A stored passkey can't be read with the configured key."""


class PasskeyCipher:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, passkey: str) -> str:
        return self._fernet.encrypt(passkey.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise MpesaCredentialsError(
                "A gym's M-Pesa passkey can't be decrypted: was "
                "MPESA_CREDENTIALS_KEY changed?"
            ) from exc
