"""Africa's Talking SMS adapter (SMS_PROVIDER=africastalking).

Built from Africa's Talking's help centre and official SDKs (checked
9 Oct 2026). It has not yet sent a real message:

- POST https://api.africastalking.com/version1/messaging (live) or
  https://api.sandbox.africastalking.com/version1/messaging (sandbox),
  form-encoded, headers apiKey and Accept: application/json. This is the
  endpoint the official Python and Node SDKs use.
- Fields: username (always "sandbox" in the sandbox), to (+ and country
  code), message, optional from (registered sender ID or shortcode;
  Africa's Talking's default sender is used otherwise), bulkSMSMode=1 as the
  SDKs send it.
- Success is HTTP 201 with SMSMessageData.Recipients[] holding statusCode,
  status, number, cost and messageId.
- Per-recipient statusCode: 100 Processed, 101 Sent, 102 Queued are
  accepted; 401 RiskHold, 402 InvalidSenderId, 403 InvalidPhoneNumber,
  404 UnsupportedNumberType, 405 InsufficientBalance, 406 UserInBlacklist,
  407 CouldNotRoute, 500 InternalServerError, 501 GatewayError,
  502 RejectedByGateway are not.

Delivery-report callbacks aren't handled yet: their field names and any
authenticity check aren't in the documentation we could confirm.
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from app.core.config import ConfigurationError, Settings
from app.integrations.http_errors import transport_error
from app.integrations.sms.base import SMSDeliveryError
from app.integrations.sms.messages import render_otp_message

logger = logging.getLogger(__name__)

_BASE_URLS = {
    "live": "https://api.africastalking.com",
    "sandbox": "https://api.sandbox.africastalking.com",
}

# Accepted by Africa's Talking (not proof of delivery).
_ACCEPTED = {100, 101, 102}

# Per-recipient statusCode -> (reason, retryable)
_STATUS_CODES: dict[int, tuple[str, bool]] = {
    401: ("provider_rejected", False),  # RiskHold
    402: ("sender_id_rejected", False),
    403: ("invalid_recipient", False),
    404: ("invalid_recipient", False),  # UnsupportedNumberType
    405: ("insufficient_balance", False),
    406: ("recipient_blocked", False),
    407: ("provider_rejected", False),  # CouldNotRoute
    500: ("provider_unavailable", True),
    501: ("provider_unavailable", True),
    502: ("provider_rejected", False),  # RejectedByGateway
}


@dataclass(frozen=True)
class AfricasTalkingConfig:
    base_url: str
    username: str
    api_key: SecretStr
    sender_id: str | None
    timeout_seconds: float

    @classmethod
    def from_settings(cls, settings: Settings) -> "AfricasTalkingConfig":
        environment = settings.africastalking_environment
        username = settings.africastalking_username
        api_key = settings.africastalking_api_key
        if environment is None or not username or api_key is None:
            raise ConfigurationError(
                "SMS_PROVIDER=africastalking is missing its settings."
            )
        return cls(
            base_url=_BASE_URLS[environment],
            username=username,
            api_key=api_key,
            sender_id=settings.africastalking_sender_id or None,
            timeout_seconds=settings.sms_send_timeout_seconds,
        )

    @property
    def send_url(self) -> str:
        return f"{self.base_url}/version1/messaging"


def _first_recipient(payload: Any) -> dict[str, Any]:
    recipients = payload["SMSMessageData"]["Recipients"]
    if not isinstance(recipients, list) or not recipients:
        raise ValueError("no recipients")
    recipient = recipients[0]
    if not isinstance(recipient, dict):
        raise TypeError("unexpected recipient")
    return recipient


class AfricasTalkingSMSProvider:
    """Sends sign-in codes through Africa's Talking's messaging endpoint."""

    def __init__(
        self, config: AfricasTalkingConfig, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._config = config
        self._client = client

    async def send_otp(
        self,
        *,
        phone_number: str,
        otp_code: str,
        expires_in_seconds: int,
    ) -> str | None:
        form = {
            "username": self._config.username,
            "to": phone_number,
            "message": render_otp_message(
                otp_code=otp_code, expires_in_seconds=expires_in_seconds
            ),
            "bulkSMSMode": "1",
        }
        if self._config.sender_id:
            form["from"] = self._config.sender_id
        headers = {
            "apiKey": self._config.api_key.get_secret_value(),
            "Accept": "application/json",
        }
        try:
            if self._client is not None:
                response = await self._client.post(
                    self._config.send_url, data=form, headers=headers
                )
            else:
                async with httpx.AsyncClient(
                    timeout=self._config.timeout_seconds
                ) as client:
                    response = await client.post(
                        self._config.send_url, data=form, headers=headers
                    )
        except httpx.TransportError as exc:
            raise transport_error(exc, SMSDeliveryError) from exc

        if response.status_code in {401, 403}:
            raise self._fail("unauthorized", False, f"http_{response.status_code}")
        if response.status_code == 429:
            raise self._fail("rate_limited", True, "http_429")
        if response.status_code >= 500:
            raise self._fail(
                "provider_unavailable", True, f"http_{response.status_code}"
            )
        if not response.is_success:
            raise self._fail("provider_rejected", False, f"http_{response.status_code}")

        try:
            recipient = _first_recipient(response.json())
            status_code = int(recipient["statusCode"])
        except (ValueError, TypeError, KeyError) as exc:
            # A success status we can't read: the message may have gone out.
            raise SMSDeliveryError("malformed_response", outcome_unknown=True) from exc

        if status_code in _ACCEPTED:
            message_id = recipient.get("messageId")
            return str(message_id) if message_id not in (None, "", "None") else None
        reason, retryable = _STATUS_CODES.get(status_code, ("provider_rejected", False))
        raise self._fail(reason, retryable, str(status_code))

    @staticmethod
    def _fail(reason: str, retryable: bool, code: str) -> SMSDeliveryError:
        # Only the code is logged; the status text can echo the number.
        logger.warning(
            "Africa's Talking SMS send failed: reason=%s code=%s", reason, code
        )
        return SMSDeliveryError(reason, retryable=retryable, provider_code=code)
