from typing import Protocol

from app.integrations.delivery import OTPDeliveryError, OTPSender


class SMSDeliveryError(OTPDeliveryError):
    """Raised by an SMS provider when a message could not be handed over.

    Providers raise this for every delivery failure they can detect: the
    provider rejected the request, timed out, was unreachable or answered with
    a response that could not be understood. The message must never contain
    the OTP or any credential, because callers may log it.
    """


class SMSProvider(OTPSender, Protocol):
    """Interface implemented by all SMS providers.

    Contract:
    - Return normally only when the provider has accepted the message.
    - Raise SMSDeliveryError for any failure; never return silently on error.
    - Never log the OTP code or provider credentials.
    - Respect cancellation: the caller enforces an overall timeout.
    """
