from functools import lru_cache

from app.core.config import Settings, get_settings
from app.integrations.mpesa.base import MpesaAccount, MpesaGateway
from app.integrations.mpesa.daraja import BASE_URLS, DarajaGateway
from app.integrations.mpesa.simulated import SimulatedMpesaGateway


def build_mpesa_gateway(settings: Settings) -> MpesaGateway | None:
    """The configured gateway, or None when M-Pesa is switched off."""

    if settings.mpesa_mode == "disabled":
        return None
    if settings.mpesa_mode == "simulated":
        return SimulatedMpesaGateway()
    # SWETO's own Daraja app: used only for accounts without their own keys
    # (sandbox and testing). In production every gym brings its own app.
    key, secret = settings.mpesa_consumer_key, settings.mpesa_consumer_secret
    return DarajaGateway(
        base_url=BASE_URLS[settings.mpesa_mode],
        consumer_key=key.get_secret_value() if key else None,
        consumer_secret=secret.get_secret_value() if secret else None,
        timeout_seconds=settings.mpesa_timeout_seconds,
    )


def default_mpesa_account(settings: Settings) -> MpesaAccount | None:
    """The account in settings, used for gyms without their own outside
    production (the sandbox shortcode, or anything in simulated mode)."""

    if settings.mpesa_mode == "production":
        return None
    if settings.mpesa_mode == "simulated":
        return MpesaAccount(
            shortcode=settings.mpesa_shortcode or "174379",
            passkey="simulated",
            transaction_type=settings.mpesa_transaction_type,
            party_b=settings.mpesa_party_b or settings.mpesa_shortcode or "174379",
        )
    if not (settings.mpesa_shortcode and settings.mpesa_passkey):
        return None
    return MpesaAccount(
        shortcode=settings.mpesa_shortcode,
        passkey=settings.mpesa_passkey.get_secret_value(),
        transaction_type=settings.mpesa_transaction_type,
        party_b=settings.mpesa_party_b or settings.mpesa_shortcode,
    )


@lru_cache
def _cached_gateway() -> MpesaGateway | None:
    return build_mpesa_gateway(get_settings())


def get_mpesa_gateway() -> MpesaGateway | None:
    """FastAPI dependency: one gateway (and token cache) per process."""

    return _cached_gateway()
