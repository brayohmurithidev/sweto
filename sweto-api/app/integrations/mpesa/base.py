"""M-Pesa STK Push ("Lipa na M-Pesa Online") as SWETO uses it."""

from dataclasses import dataclass
from typing import Protocol


class MpesaError(Exception):
    """A request to M-Pesa failed.

    ``reason`` is a short, stable category safe to log (never a phone number
    or credential). ``outcome_unknown`` is True when the request may have
    reached M-Pesa (a timeout, a dropped connection): a prompt may still pop
    up on the member's phone, so don't send another straight away.
    """

    def __init__(
        self,
        reason: str,
        *,
        provider_code: str | None = None,
        outcome_unknown: bool = False,
    ) -> None:
        self.reason = reason
        self.provider_code = provider_code
        self.outcome_unknown = outcome_unknown
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class MpesaAccount:
    """The shortcode an STK Push is sent from and paid into.

    Pay Bill: ``party_b`` is the shortcode itself. Till (Buy Goods):
    ``shortcode`` is the store/head-office number the passkey belongs to and
    ``party_b`` is the till number the money goes to.
    """

    shortcode: str
    passkey: str
    transaction_type: str
    party_b: str
    # The gym's own Daraja app. None: the gateway's default app (sandbox and
    # testing only).
    consumer_key: str | None = None
    consumer_secret: str | None = None

    def __repr__(self) -> str:  # never print the passkey
        return f"MpesaAccount(shortcode={self.shortcode!r}, party_b={self.party_b!r})"


@dataclass(frozen=True, slots=True)
class StkPushAccepted:
    merchant_request_id: str
    checkout_request_id: str


@dataclass(frozen=True, slots=True)
class StkResult:
    """The outcome of one STK Push, from a callback or a status query."""

    result_code: int
    result_desc: str
    receipt: str | None = None
    amount: int | None = None

    @property
    def succeeded(self) -> bool:
        return self.result_code == 0


class MpesaGateway(Protocol):
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
        """Send the PIN prompt to an E.164 phone. Raise MpesaError on failure."""
        ...

    async def stk_query(
        self, *, account: MpesaAccount, checkout_request_id: str
    ) -> StkResult | None:
        """The final result, or None while the member hasn't answered yet."""
        ...


# Result codes worth telling staff about in plain words.
RESULT_MESSAGES = {
    0: "Paid.",
    1: "The member's M-Pesa balance is too low.",
    1032: "The member cancelled the M-Pesa prompt.",
    1037: "The member didn't answer the M-Pesa prompt in time.",
    2001: "The member entered the wrong M-Pesa PIN.",
}


def result_message(result_code: int | None) -> str:
    if result_code is None:
        return "M-Pesa didn't confirm the payment."
    return RESULT_MESSAGES.get(result_code, "M-Pesa declined the payment.")
