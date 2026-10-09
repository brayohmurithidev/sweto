"""Advanta SMS adapter (SMS_PROVIDER=advanta).

Built from Advanta's public API page, https://www.advantasms.com/bulksms-api
(checked 9 Oct 2026). It has not yet sent a real message:

- POST {base}/api/services/sendsms/ with JSON
  {apikey, partnerID, message, shortcode, mobile}; mobile without "+".
- The reply is {"responses": [{"respose-code": 200, "response-description",
  "mobile", "messageid", "networkid"}]}. The page spells the key
  "respose-code"; "response-code" is accepted too.
- Result codes: 200 success; 1001 invalid sender ID; 1002 network not
  allowed; 1003 invalid mobile number; 1004 low credit; 1005/1007 system
  error; 1006 invalid credentials; 1009/1010 unsupported data/request type;
  4090 internal error (retry later); 4091 no partner ID; 4092 no API key;
  4093 details not found.

Advanta delivery reports are pulled through getdlr, whose reply the page
doesn't document, so delivery status isn't tracked for Advanta yet.
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

# Advanta result code -> (reason, retryable)
_RESULT_CODES: dict[int, tuple[str, bool]] = {
    1001: ("sender_id_rejected", False),
    1002: ("invalid_recipient", False),
    1003: ("invalid_recipient", False),
    1004: ("insufficient_balance", False),
    1005: ("provider_unavailable", True),
    1006: ("unauthorized", False),
    1007: ("provider_unavailable", True),
    1009: ("invalid_request", False),
    1010: ("invalid_request", False),
    4090: ("provider_unavailable", True),
    4091: ("unauthorized", False),
    4092: ("unauthorized", False),
    4093: ("provider_rejected", False),
}


@dataclass(frozen=True)
class AdvantaConfig:
    base_url: str
    api_key: SecretStr
    partner_id: str
    shortcode: str
    timeout_seconds: float

    @classmethod
    def from_settings(cls, settings: Settings) -> "AdvantaConfig":
        api_key = settings.advanta_api_key
        partner_id = settings.advanta_partner_id
        shortcode = settings.advanta_shortcode
        if api_key is None or not partner_id or not shortcode:
            raise ConfigurationError("SMS_PROVIDER=advanta is missing its settings.")
        return cls(
            base_url=settings.advanta_base_url.rstrip("/"),
            api_key=api_key,
            partner_id=partner_id,
            shortcode=shortcode,
            timeout_seconds=settings.sms_send_timeout_seconds,
        )

    @property
    def send_url(self) -> str:
        return f"{self.base_url}/api/services/sendsms/"


def _result_code(item: dict[str, Any]) -> int | None:
    raw = item.get("respose-code", item.get("response-code"))
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


class AdvantaSMSProvider:
    """Sends sign-in codes through Advanta's sendsms endpoint."""

    def __init__(
        self, config: AdvantaConfig, *, client: httpx.AsyncClient | None = None
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
        body = {
            "apikey": self._config.api_key.get_secret_value(),
            "partnerID": self._config.partner_id,
            "message": render_otp_message(
                otp_code=otp_code, expires_in_seconds=expires_in_seconds
            ),
            "shortcode": self._config.shortcode,
            "mobile": phone_number.removeprefix("+"),
        }
        try:
            if self._client is not None:
                response = await self._client.post(self._config.send_url, json=body)
            else:
                async with httpx.AsyncClient(
                    timeout=self._config.timeout_seconds
                ) as client:
                    response = await client.post(self._config.send_url, json=body)
        except httpx.TransportError as exc:
            raise transport_error(exc, SMSDeliveryError) from exc

        if response.status_code in {401, 403}:
            raise self._fail("unauthorized", False, f"http_{response.status_code}")
        if response.status_code >= 500:
            raise self._fail(
                "provider_unavailable", True, f"http_{response.status_code}"
            )
        if not response.is_success:
            raise self._fail("provider_rejected", False, f"http_{response.status_code}")

        try:
            payload = response.json()
            items = payload.get("responses") if isinstance(payload, dict) else None
            item = items[0] if isinstance(items, list) and items else payload
            if not isinstance(item, dict):
                raise TypeError("unexpected response shape")
        except (ValueError, TypeError, AttributeError) as exc:
            # A success status we can't read: the message may have gone out.
            raise SMSDeliveryError("malformed_response", outcome_unknown=True) from exc

        code = _result_code(item)
        if code == 200:
            message_id = item.get("messageid")
            return str(message_id) if message_id not in (None, "") else None
        if code is None:
            raise SMSDeliveryError("malformed_response", outcome_unknown=True)
        reason, retryable = _RESULT_CODES.get(code, ("provider_rejected", False))
        raise self._fail(reason, retryable, str(code))

    @staticmethod
    def _fail(reason: str, retryable: bool, code: str) -> SMSDeliveryError:
        # Only the code is logged; Advanta's description can echo the number.
        logger.warning("Advanta SMS send failed: reason=%s code=%s", reason, code)
        return SMSDeliveryError(reason, retryable=retryable, provider_code=code)
