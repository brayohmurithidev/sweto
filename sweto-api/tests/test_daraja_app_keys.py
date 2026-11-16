"""Each gym's prompts go through its own Daraja app (Safaricom binds an app
to the shortcode it went live on)."""

import base64

import httpx
import pytest

from app.integrations.mpesa.base import MpesaAccount, MpesaError
from app.integrations.mpesa.daraja import DarajaGateway


def account(key: str | None, secret: str | None, shortcode: str) -> MpesaAccount:
    return MpesaAccount(
        shortcode=shortcode,
        passkey="p" * 40,
        transaction_type="CustomerPayBillOnline",
        party_b=shortcode,
        consumer_key=key,
        consumer_secret=secret,
    )


class Daraja:
    """Records which app asked for a token and which token each call used."""

    def __init__(self) -> None:
        self.token_requests: list[str] = []
        self.calls: list[tuple[str, str]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/v1/generate":
            basic = request.headers["Authorization"].removeprefix("Basic ")
            key = base64.b64decode(basic).decode().split(":")[0]
            self.token_requests.append(key)
            return httpx.Response(
                200, json={"access_token": f"token-{key}", "expires_in": "3599"}
            )
        bearer = request.headers["Authorization"].removeprefix("Bearer ")
        shortcode = str(request.read().decode()).split('"BusinessShortCode":"')[1]
        self.calls.append((bearer, shortcode.split('"')[0]))
        return httpx.Response(
            200,
            json={
                "ResponseCode": "0",
                "MerchantRequestID": "m-1",
                "CheckoutRequestID": "c-1",
            },
        )


def gateway(
    daraja: Daraja, *, key: str | None = None, secret: str | None = None
) -> DarajaGateway:
    return DarajaGateway(
        base_url="https://daraja.test",
        consumer_key=key,
        consumer_secret=secret,
        timeout_seconds=5,
        client=httpx.AsyncClient(transport=httpx.MockTransport(daraja.handler)),
    )


async def push(gw: DarajaGateway, acc: MpesaAccount) -> None:
    await gw.stk_push(
        account=acc,
        phone_number="+254712345678",
        amount=10,
        account_reference="Gym",
        description="Membership",
        callback_url="https://api.test/cb",
    )


async def test_each_gym_uses_its_own_app_and_token() -> None:
    daraja = Daraja()
    gw = gateway(daraja, key="sweto-app", secret="sweto-secret")
    gym_a = account("gym-a-key", "gym-a-secret", "111111")
    gym_b = account("gym-b-key", "gym-b-secret", "222222")

    await push(gw, gym_a)
    await push(gw, gym_b)
    await push(gw, gym_a)

    # One token per app, reused while it is valid; never SWETO's app.
    assert daraja.token_requests == ["gym-a-key", "gym-b-key"]
    assert daraja.calls == [
        ("token-gym-a-key", "111111"),
        ("token-gym-b-key", "222222"),
        ("token-gym-a-key", "111111"),
    ]


async def test_a_gym_without_keys_uses_swetos_app_when_there_is_one() -> None:
    daraja = Daraja()
    await push(gateway(daraja, key="sweto-app", secret="s"), account(None, None, "1"))
    assert daraja.token_requests == ["sweto-app"]

    with pytest.raises(MpesaError) as error:
        await push(gateway(Daraja()), account(None, None, "174379"))
    assert error.value.reason == "not_configured"
