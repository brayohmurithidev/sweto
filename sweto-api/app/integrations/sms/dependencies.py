from functools import lru_cache

from app.core.config import get_settings
from app.integrations.sms.base import SMSProvider
from app.integrations.sms.console import ConsoleSMSProvider


@lru_cache
def get_sms_provider() -> SMSProvider:
    """Return the SMS provider configured for this environment."""

    settings = get_settings()

    if settings.sms_provider == "console":
        return ConsoleSMSProvider()

    raise RuntimeError(f"Unsupported SMS provider: {settings.sms_provider}")
