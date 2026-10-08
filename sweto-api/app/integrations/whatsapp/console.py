import logging

logger = logging.getLogger(__name__)


class ConsoleWhatsAppProvider:
    """Development provider that writes WhatsApp OTPs to application logs."""

    async def send_otp(
        self,
        *,
        phone_number: str,
        otp_code: str,
        expires_in_seconds: int,
    ) -> str | None:
        logger.warning(
            "SWETO DEVELOPMENT WHATSAPP OTP | phone=%s code=%s expires_in=%ss",
            phone_number,
            otp_code,
            expires_in_seconds,
        )
        return None
