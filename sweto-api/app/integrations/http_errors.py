"""Turning HTTP client failures into provider-neutral delivery errors."""

import httpx

from app.integrations.delivery import OTPDeliveryError


def transport_error[ErrorT: OTPDeliveryError](
    exc: httpx.HTTPError, error_class: type[ErrorT]
) -> ErrorT:
    """Classify a failure that happened before any HTTP response arrived.

    A connection that was never made means the provider got nothing, so the
    message was certainly not sent. Anything later (a read timeout, a dropped
    connection) may have reached the provider: the outcome is unknown.
    """

    if isinstance(exc, httpx.ConnectTimeout | httpx.ConnectError):
        return error_class("provider_unreachable")
    if isinstance(exc, httpx.TimeoutException):
        return error_class("timeout", outcome_unknown=True)
    return error_class("provider_unreachable", outcome_unknown=True)
