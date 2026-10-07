import logging

logger = logging.getLogger(__name__)


class ConsoleSMSProvider:
    """Development provider that writes OTP messages to application logs."""

    async def send_otp(
        self,
        *,
        phone_number: str,
        otp_code: str,
        expires_in_seconds: int,
    ) -> None:
        logger.warning(
            "SWETO DEVELOPMENT OTP | phone=%s code=%s expires_in=%ss",
            phone_number,
            otp_code,
            expires_in_seconds,
        )
