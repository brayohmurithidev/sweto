from functools import lru_cache

from app.core.config import get_settings
from app.integrations.sms.base import SMSProvider
from app.integrations.sms.registry import build_sms_provider


@lru_cache
def get_sms_provider() -> SMSProvider:
    """Return the SMS provider configured for this environment."""

    return build_sms_provider(get_settings())
