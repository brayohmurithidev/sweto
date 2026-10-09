"""Resolving SMS_PROVIDER to an SMS adapter.

Every adapter implements SMSProvider, so the auth service never knows which
one is in use; switching provider is a configuration change. There is no
automatic fallback between providers: a send that timed out may still
arrive, so retrying it elsewhere could deliver two codes.
"""

from collections.abc import Callable

import httpx

from app.core.config import ConfigurationError, Settings
from app.integrations.sms.advanta import AdvantaConfig, AdvantaSMSProvider
from app.integrations.sms.africastalking import (
    AfricasTalkingConfig,
    AfricasTalkingSMSProvider,
)
from app.integrations.sms.base import SMSProvider
from app.integrations.sms.console import ConsoleSMSProvider

SMSProviderFactory = Callable[[Settings, httpx.AsyncClient | None], SMSProvider]

SMS_PROVIDERS: dict[str, SMSProviderFactory] = {
    "console": lambda settings, client: ConsoleSMSProvider(),
    "advanta": lambda settings, client: AdvantaSMSProvider(
        AdvantaConfig.from_settings(settings), client=client
    ),
    "africastalking": lambda settings, client: AfricasTalkingSMSProvider(
        AfricasTalkingConfig.from_settings(settings), client=client
    ),
}


def build_sms_provider(
    settings: Settings, *, client: httpx.AsyncClient | None = None
) -> SMSProvider:
    """Build the configured adapter, or fail clearly. Never falls back.

    ``client`` replaces the adapter's HTTP client (tests use a mock
    transport); by default each send opens its own client with the timeout.
    """

    factory = SMS_PROVIDERS.get(settings.sms_provider)
    if factory is None:
        raise ConfigurationError(
            f"Unknown SMS_PROVIDER '{settings.sms_provider}'. "
            f"Use one of: {', '.join(sorted(SMS_PROVIDERS))}."
        )
    return factory(settings, client)
