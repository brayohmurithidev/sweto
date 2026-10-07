from typing import Protocol


class SMSProvider(Protocol):
    """Interface implemented by all SMS providers."""

    async def send_otp(
        self,
        *,
        phone_number: str,
        otp_code: str,
        expires_in_seconds: int,
    ) -> None:
        """Send an authentication OTP."""
        ...
