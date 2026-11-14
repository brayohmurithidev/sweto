from functools import lru_cache

from app.core.config import Settings, get_settings
from app.integrations.mpesa.base import MpesaGateway
from app.integrations.mpesa.daraja import BASE_URLS, DarajaGateway
from app.integrations.mpesa.simulated import SimulatedMpesaGateway


def build_mpesa_gateway(settings: Settings) -> MpesaGateway | None:
    """The configured gateway, or None when M-Pesa is switched off."""

    if settings.mpesa_mode == "disabled":
        return None
    if settings.mpesa_mode == "simulated":
        return SimulatedMpesaGateway()
    assert settings.mpesa_consumer_key and settings.mpesa_consumer_secret
    assert settings.mpesa_shortcode and settings.mpesa_passkey
    return DarajaGateway(
        base_url=BASE_URLS[settings.mpesa_mode],
        consumer_key=settings.mpesa_consumer_key.get_secret_value(),
        consumer_secret=settings.mpesa_consumer_secret.get_secret_value(),
        shortcode=settings.mpesa_shortcode,
        passkey=settings.mpesa_passkey.get_secret_value(),
        transaction_type=settings.mpesa_transaction_type,
        party_b=settings.mpesa_party_b or settings.mpesa_shortcode,
        timeout_seconds=settings.mpesa_timeout_seconds,
    )


@lru_cache
def _cached_gateway() -> MpesaGateway | None:
    return build_mpesa_gateway(get_settings())


def get_mpesa_gateway() -> MpesaGateway | None:
    """FastAPI dependency: one gateway (and token cache) per process."""

    return _cached_gateway()
