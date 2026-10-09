"""Contract shared by every provider that delivers one-time passwords.

Authentication only talks to this contract. SMS (Advanta, Kenya) and WhatsApp
(other countries) providers implement it, so a channel or provider can be added
or swapped without changing the authentication flow.
"""

from typing import Protocol


class OTPDeliveryError(Exception):
    """Raised by a provider when a code could not be handed over.

    Providers raise this (or a channel-specific subclass) for every failure
    they can detect: the provider rejected the request, timed out, was
    unreachable or answered with a response that could not be understood.
    ``reason`` is a short, stable category such as ``provider_rejected``. It
    must never contain the OTP or any credential, because callers log it.
    ``provider_code`` is the provider's own error code (for example Meta's
    ``131026``), kept for the audit log; never put provider messages here,
    because they can contain the recipient's number.
    ``outcome_unknown`` is True when the request may have reached the
    provider (a read timeout, a dropped connection, an unreadable success
    response): the message may still arrive. Never retry such a send through
    another provider, or the user can get two codes.
    """

    def __init__(
        self,
        reason: str,
        *,
        retryable: bool = True,
        provider_code: str | None = None,
        outcome_unknown: bool = False,
    ) -> None:
        self.reason = reason
        self.retryable = retryable
        self.provider_code = provider_code
        self.outcome_unknown = outcome_unknown
        super().__init__(reason)


class OTPSender(Protocol):
    """Sends an authentication code to one E.164 phone number.

    Contract:
    - Return normally only when the provider has accepted the message, with
      the provider's message ID when it has one (used to match delivery
      reports to the challenge), otherwise None. Acceptance is not proof of
      delivery; channels that report delivery later (WhatsApp) do so through
      their own callbacks.
    - Raise OTPDeliveryError for any failure; never return silently on error.
    - Never log the OTP code or provider credentials.
    - Respect cancellation: the caller enforces an overall timeout.
    """

    async def send_otp(
        self,
        *,
        phone_number: str,
        otp_code: str,
        expires_in_seconds: int,
    ) -> str | None:
        """Send an authentication OTP to an E.164 phone number."""
        ...
