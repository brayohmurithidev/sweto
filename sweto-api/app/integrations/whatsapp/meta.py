"""WhatsApp sign-in codes through Meta's WhatsApp Cloud API.

Sends the approved AUTHENTICATION template (copy-code button) to one number:
``POST {base}/{version}/{phone_number_id}/messages``. Only the request
format documented by Meta is used; see docs/whatsapp-otp.md for sources.

A successful response means Meta accepted the message, not that it arrived.
Delivery is reported later through the status webhook.
"""

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.whatsapp.base import WhatsAppDeliveryError

# Meta error codes, grouped by how SWETO reacts. Source: WhatsApp Cloud API
# error codes reference (checked 8 Oct 2026).
_AUTH_ERRORS = frozenset({0, 3, 10, 190, 200, 131005})
_RATE_LIMIT_ERRORS = frozenset({4, 80007, 130429, 131048, 131056})
_RECIPIENT_ERRORS = frozenset({131026, 131049})
_TEMPLATE_ERRORS = frozenset({132000, 132001, 132005, 132007, 132012, 132015, 132016})
_REQUEST_ERRORS = frozenset({100, 131008, 131009})
_SERVICE_ERRORS = frozenset({1, 2, 131000, 131016})


@dataclass(frozen=True)
class MetaWhatsAppConfig:
    base_url: str
    api_version: str
    phone_number_id: str
    access_token: SecretStr
    template_name: str
    template_language: str
    timeout_seconds: float

    @classmethod
    def from_settings(cls, settings: Settings) -> "MetaWhatsAppConfig":
        # Settings validation guarantees these are present for provider=meta.
        assert settings.meta_graph_api_version is not None
        assert settings.meta_whatsapp_phone_number_id is not None
        assert settings.meta_whatsapp_access_token is not None
        assert settings.meta_whatsapp_otp_template_name is not None
        assert settings.meta_whatsapp_otp_template_language is not None
        return cls(
            base_url=settings.meta_graph_api_base_url.rstrip("/"),
            api_version=settings.meta_graph_api_version,
            phone_number_id=settings.meta_whatsapp_phone_number_id,
            access_token=settings.meta_whatsapp_access_token,
            template_name=settings.meta_whatsapp_otp_template_name,
            template_language=settings.meta_whatsapp_otp_template_language,
            timeout_seconds=settings.whatsapp_send_timeout_seconds,
        )

    @property
    def messages_url(self) -> str:
        return f"{self.base_url}/{self.api_version}/{self.phone_number_id}/messages"


def build_authentication_template_message(
    *, phone_number: str, otp_code: str, template_name: str, language: str
) -> dict[str, Any]:
    """Return the Cloud API body for an authentication template message.

    The code goes in the body parameter and in the copy-code button
    parameter, as Meta's authentication template example requires.

    ``to`` keeps the leading ``+``. Meta prepends the business number's own
    country code to numbers sent without it, which would misdeliver codes
    to other countries.
    """

    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": [
                {"type": "body", "parameters": [{"type": "text", "text": otp_code}]},
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": otp_code}],
                },
            ],
        },
    }


def _error_from_response(response: httpx.Response) -> WhatsAppDeliveryError:
    """Map a non-2xx Graph API response to a stable delivery error.

    Only the numeric error code is kept. Meta's message and details can
    contain the recipient's number, so they are never copied.
    """

    code: int | None = None
    try:
        body = response.json()
        raw_code = body.get("error", {}).get("code") if isinstance(body, dict) else None
        code = int(raw_code) if raw_code is not None else None
    except (ValueError, TypeError, AttributeError):
        code = None
    provider_code = str(code) if code is not None else f"http_{response.status_code}"

    def error(reason: str, retryable: bool) -> WhatsAppDeliveryError:
        return WhatsAppDeliveryError(
            reason, retryable=retryable, provider_code=provider_code
        )

    status = response.status_code
    if code in _AUTH_ERRORS or status in {401, 403}:
        return error("unauthorized", False)
    if code in _RATE_LIMIT_ERRORS or status == 429:
        return error("rate_limited", True)
    if code in _RECIPIENT_ERRORS:
        return error("recipient_undeliverable", False)
    if code in _TEMPLATE_ERRORS:
        return error("template_rejected", False)
    if code in _REQUEST_ERRORS:
        return error("invalid_request", False)
    if code in _SERVICE_ERRORS or status >= 500:
        return error("provider_unavailable", True)
    return error("provider_rejected", False)


class MetaWhatsAppProvider:
    """WhatsAppOTPProvider for Meta's WhatsApp Cloud API."""

    def __init__(
        self,
        config: MetaWhatsAppConfig,
        *,
        client: httpx.AsyncClient | None = None,
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
        # expires_in_seconds is not sent: the expiry line is fixed in the
        # approved template (code_expiration_minutes) and must match
        # OTP_EXPIRY_SECONDS.
        body = build_authentication_template_message(
            phone_number=phone_number,
            otp_code=otp_code,
            template_name=self._config.template_name,
            language=self._config.template_language,
        )
        headers = {
            "Authorization": (f"Bearer {self._config.access_token.get_secret_value()}"),
            "Content-Type": "application/json",
        }
        try:
            if self._client is not None:
                response = await self._client.post(
                    self._config.messages_url,
                    json=body,
                    headers=headers,
                    timeout=self._config.timeout_seconds,
                )
            else:
                async with httpx.AsyncClient(
                    timeout=self._config.timeout_seconds
                ) as client:
                    response = await client.post(
                        self._config.messages_url, json=body, headers=headers
                    )
        except httpx.TimeoutException as exc:
            raise WhatsAppDeliveryError("timeout") from exc
        except httpx.TransportError as exc:
            raise WhatsAppDeliveryError("provider_unreachable") from exc

        if not response.is_success:
            raise _error_from_response(response)

        try:
            payload = response.json()
            message_id = payload["messages"][0]["id"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise WhatsAppDeliveryError("malformed_response") from exc
        if not isinstance(message_id, str) or not message_id:
            raise WhatsAppDeliveryError("malformed_response")
        return message_id
