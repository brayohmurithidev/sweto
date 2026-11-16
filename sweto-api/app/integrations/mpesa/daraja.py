"""Safaricom Daraja client for STK Push and its status query."""

import base64
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from app.integrations.mpesa.base import (
    MpesaAccount,
    MpesaError,
    StkPushAccepted,
    StkResult,
)

logger = logging.getLogger(__name__)

BASE_URLS = {
    "sandbox": "https://sandbox.safaricom.co.ke",
    "production": "https://api.safaricom.co.ke",
}
# Daraja answers a status query for an unanswered prompt with this error.
_STILL_PROCESSING = "500.001.1001"
_NAIROBI = ZoneInfo("Africa/Nairobi")


class DarajaGateway:
    def __init__(
        self,
        *,
        base_url: str,
        consumer_key: str | None,
        consumer_secret: str | None,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._timeout = timeout_seconds
        self._client = client
        # One token per Daraja app: (token, monotonic expiry) by consumer key.
        self._tokens: dict[str, tuple[str, float]] = {}

    async def stk_push(
        self,
        *,
        account: MpesaAccount,
        phone_number: str,
        amount: int,
        account_reference: str,
        description: str,
        callback_url: str,
    ) -> StkPushAccepted:
        msisdn = phone_number.removeprefix("+")
        body = {
            **self._credentials(account),
            "TransactionType": account.transaction_type,
            "Amount": amount,
            "PartyA": msisdn,
            "PartyB": account.party_b,
            "PhoneNumber": msisdn,
            "CallBackURL": callback_url,
            # Daraja limits: 12 and 13 characters.
            "AccountReference": account_reference[:12],
            "TransactionDesc": description[:13],
        }
        data = await self._post("/mpesa/stkpush/v1/processrequest", body, account)
        if str(data.get("ResponseCode")) != "0":
            raise MpesaError(
                "request_rejected", provider_code=str(data.get("ResponseCode"))
            )
        try:
            return StkPushAccepted(
                merchant_request_id=str(data["MerchantRequestID"]),
                checkout_request_id=str(data["CheckoutRequestID"]),
            )
        except KeyError as exc:
            raise MpesaError("malformed_response", outcome_unknown=True) from exc

    async def stk_query(
        self, *, account: MpesaAccount, checkout_request_id: str
    ) -> StkResult | None:
        body: dict[str, object] = {
            **self._credentials(account),
            "CheckoutRequestID": checkout_request_id,
        }
        try:
            data = await self._post("/mpesa/stkpushquery/v1/query", body, account)
        except MpesaError as error:
            if error.provider_code == _STILL_PROCESSING:
                return None
            raise
        try:
            return StkResult(
                result_code=int(str(data["ResultCode"])),
                result_desc=str(data.get("ResultDesc", ""))[:255],
            )
        except (KeyError, ValueError) as exc:
            raise MpesaError("malformed_response") from exc

    @staticmethod
    def _credentials(account: MpesaAccount) -> dict[str, str]:
        timestamp = datetime.now(_NAIROBI).strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{account.shortcode}{account.passkey}{timestamp}".encode()
        ).decode()
        return {
            "BusinessShortCode": account.shortcode,
            "Password": password,
            "Timestamp": timestamp,
        }

    def _app_keys(self, account: MpesaAccount) -> tuple[str, str]:
        """The Daraja app this account's requests go through: the gym's own,
        else the default one (sandbox and testing)."""

        if account.consumer_key and account.consumer_secret:
            return account.consumer_key, account.consumer_secret
        if self._consumer_key and self._consumer_secret:
            return self._consumer_key, self._consumer_secret
        raise MpesaError("not_configured")

    async def _access_token(
        self, client: httpx.AsyncClient, account: MpesaAccount
    ) -> str:
        key, secret = self._app_keys(account)
        cached = self._tokens.get(key)
        if cached and time.monotonic() < cached[1]:
            return cached[0]
        try:
            response = await client.get(
                f"{self._base_url}/oauth/v1/generate",
                params={"grant_type": "client_credentials"},
                auth=(key, secret),
            )
        except httpx.TransportError as exc:
            raise MpesaError("unreachable") from exc
        if response.status_code in {400, 401, 403}:
            raise MpesaError(
                "unauthorized", provider_code=f"http_{response.status_code}"
            )
        if not response.is_success:
            raise MpesaError(
                "unavailable", provider_code=f"http_{response.status_code}"
            )
        try:
            payload = response.json()
            token = str(payload["access_token"])
            lifetime = int(payload.get("expires_in", 3599))
        except (ValueError, KeyError, TypeError) as exc:
            raise MpesaError("malformed_response") from exc
        # Renew a minute early so a request never carries a stale token.
        self._tokens[key] = (token, time.monotonic() + max(lifetime - 60, 0))
        return token

    async def _post(
        self, path: str, body: dict[str, object], account: MpesaAccount
    ) -> dict[str, object]:
        if self._client is not None:
            return await self._post_with(self._client, path, body, account)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._post_with(client, path, body, account)

    async def _post_with(
        self,
        client: httpx.AsyncClient,
        path: str,
        body: dict[str, object],
        account: MpesaAccount,
    ) -> dict[str, object]:
        token = await self._access_token(client, account)
        try:
            response = await client.post(
                f"{self._base_url}{path}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.TimeoutException as exc:
            raise MpesaError("timeout", outcome_unknown=True) from exc
        except httpx.TransportError as exc:
            raise MpesaError("unreachable") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise MpesaError(
                "malformed_response", outcome_unknown=response.is_success
            ) from exc
        if not isinstance(data, dict):
            raise MpesaError("malformed_response", outcome_unknown=response.is_success)
        if response.status_code == 401:
            self._tokens.pop(self._app_keys(account)[0], None)
            raise MpesaError("unauthorized", provider_code="http_401")
        if not response.is_success:
            code = str(data.get("errorCode", f"http_{response.status_code}"))
            # Only the code is logged: Daraja messages can echo the number.
            if code != _STILL_PROCESSING:
                logger.warning("Daraja request failed: path=%s code=%s", path, code)
            raise MpesaError("request_rejected", provider_code=code)
        return data
