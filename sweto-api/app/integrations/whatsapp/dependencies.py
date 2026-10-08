from functools import lru_cache

from app.core.config import get_settings
from app.integrations.whatsapp.base import WhatsAppOTPProvider
from app.integrations.whatsapp.console import ConsoleWhatsAppProvider


@lru_cache
def get_whatsapp_provider() -> WhatsAppOTPProvider | None:
    """Return the configured WhatsApp provider, or None when it is disabled.

    WhatsApp is disabled until a provider has been chosen and configured.
    While disabled, sign-in codes can only be sent to SMS countries.
    """

    settings = get_settings()

    if settings.whatsapp_provider == "disabled":
        return None
    if settings.whatsapp_provider == "console":
        return ConsoleWhatsAppProvider()

    raise RuntimeError(f"Unsupported WhatsApp provider: {settings.whatsapp_provider}")
