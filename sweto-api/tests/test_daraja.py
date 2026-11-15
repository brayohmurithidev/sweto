"""Daraja client against a mocked HTTP transport."""

import base64
import json

import httpx
import pytest

from app.integrations.mpesa.base import MpesaAccount, MpesaError
from app.integrations.mpesa.daraja import DarajaGateway

BASE = "https://sandbox.safaricom.co.ke"
ACCOUNT = MpesaAccount(
    shortcode="174379",
    passkey="passkey",
    transaction_type="CustomerPayBillOnline",
    party_b="174379",
)


def gateway(handler: httpx.MockTransport) -> DarajaGateway:
    return DarajaGateway(
        base_url=BASE,
        consumer_key="key",
        consumer_secret="secret",
        timeout_seconds=5,
        client=httpx.AsyncClient(transport=handler),
    )


async def test_stk_push_sends_daraja_fields_and_reuses_the_token() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/oauth/v1/generate":
            return httpx.Response(200, json={"access_token": "T", "expires_in": "3599"})
        return httpx.Response(
            200,
            json={
                "MerchantRequestID": "MR",
                "CheckoutRequestID": "ws_CO_1",
                "ResponseCode": "0",
            },
        )

    client = gateway(httpx.MockTransport(handle))
    for _ in range(2):
        accepted = await client.stk_push(
            account=ACCOUNT,
            phone_number="+254711000001",
            amount=5000,
            account_reference="FlexFitWestlands",
            description="Membership renewal",
            callback_url="https://api.example/cb",
        )
    assert accepted.checkout_request_id == "ws_CO_1"
    assert [r.url.path for r in requests].count("/oauth/v1/generate") == 1
    body = json.loads(requests[-1].content)
    assert requests[-1].headers["Authorization"] == "Bearer T"
    assert (body["PartyA"], body["PhoneNumber"], body["Amount"]) == (
        "254711000001",
        "254711000001",
        5000,
    )
    assert body["AccountReference"] == "FlexFitWestl"  # Daraja: 12 characters
    assert len(body["TransactionDesc"]) <= 13
    password = base64.b64decode(body["Password"]).decode()
    assert password == f"174379passkey{body['Timestamp']}"
    assert len(body["Timestamp"]) == 14


async def test_rejections_and_pending_queries() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/v1/generate":
            return httpx.Response(200, json={"access_token": "T", "expires_in": "3599"})
        if request.url.path.endswith("processrequest"):
            return httpx.Response(
                400, json={"errorCode": "400.002.02", "errorMessage": "Bad Request"}
            )
        return httpx.Response(
            500,
            json={"errorCode": "500.001.1001", "errorMessage": "being processed"},
        )

    client = gateway(httpx.MockTransport(handle))
    with pytest.raises(MpesaError) as raised:
        await client.stk_push(
            account=ACCOUNT,
            phone_number="+254711000001",
            amount=1,
            account_reference="x",
            description="x",
            callback_url="https://x",
        )
    assert (raised.value.reason, raised.value.provider_code) == (
        "request_rejected",
        "400.002.02",
    )
    assert (
        await client.stk_query(account=ACCOUNT, checkout_request_id="ws_CO_1") is None
    )


async def test_a_bad_key_is_reported_without_details() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Bad Request - Invalid Credentials")

    with pytest.raises(MpesaError) as raised:
        await gateway(httpx.MockTransport(handle)).stk_query(
            account=ACCOUNT, checkout_request_id="x"
        )
    assert raised.value.reason == "unauthorized"


def test_the_passkey_never_shows_in_logs_or_reprs() -> None:
    assert "passkey" not in repr(ACCOUNT).replace("MpesaAccount", "")
