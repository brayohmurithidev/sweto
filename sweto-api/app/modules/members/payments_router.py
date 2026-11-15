import hmac
import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.integrations.mpesa.base import MpesaGateway, StkResult
from app.integrations.mpesa.dependencies import get_mpesa_gateway
from app.modules.auth.dependencies import CurrentUser
from app.modules.members.mpesa_accounts import MpesaAccounts
from app.modules.members.mpesa_service import MpesaPaymentService
from app.modules.members.router import MemberService
from app.modules.members.schemas import (
    MpesaAccountData,
    MpesaPaymentData,
    RequestMpesaPaymentRequest,
    SaveMpesaAccountRequest,
)
from app.shared.clock import Clock, get_clock
from app.shared.responses import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gyms/{gym_id}", tags=["Payments"])
callback_router = APIRouter(prefix="/payments/mpesa", tags=["Payments"])


def get_mpesa_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    settings: Annotated[Settings, Depends(get_settings)],
    gateway: Annotated[MpesaGateway | None, Depends(get_mpesa_gateway)],
    members: MemberService,
) -> MpesaPaymentService:
    return MpesaPaymentService(
        session=session,
        clock=clock,
        settings=settings,
        gateway=gateway,
        members=members,
    )


MpesaService = Annotated[MpesaPaymentService, Depends(get_mpesa_service)]


@router.post(
    "/members/{member_id}/payments/mpesa",
    response_model=APIResponse[MpesaPaymentData],
    status_code=status.HTTP_201_CREATED,
)
async def request_mpesa_payment(
    gym_id: UUID,
    member_id: UUID,
    payload: RequestMpesaPaymentRequest,
    current_user: CurrentUser,
    service: MpesaService,
) -> APIResponse[MpesaPaymentData]:
    """Send an M-Pesa PIN prompt to the member for a plan.

    The payment stays pending until M-Pesa confirms it; poll
    GET /gyms/{gym_id}/payments/{payment_id} for the outcome.
    """

    data = await service.request(
        user_id=current_user.id, gym_id=gym_id, member_id=member_id, payload=payload
    )
    return APIResponse(data=data)


@router.get("/payments/{payment_id}", response_model=APIResponse[MpesaPaymentData])
async def get_payment(
    gym_id: UUID,
    payment_id: UUID,
    current_user: CurrentUser,
    service: MpesaService,
) -> APIResponse[MpesaPaymentData]:
    """Where a payment stands: pending, completed or failed (with why)."""

    data = await service.status(
        user_id=current_user.id, gym_id=gym_id, payment_id=payment_id
    )
    return APIResponse(data=data)


_ACCEPTED = {"ResultCode": 0, "ResultDesc": "Accepted"}


@callback_router.post("/callback/{token}", include_in_schema=False)
async def mpesa_callback(
    token: str,
    settings: Annotated[Settings, Depends(get_settings)],
    service: MpesaService,
    body: Annotated[dict[str, Any], Body()],
) -> dict[str, object]:
    """Safaricom posts each STK Push result here.

    Only a request carrying the secret token is read. Anything else in the
    body that can't be matched is acknowledged and dropped, so Safaricom
    doesn't retry it forever; the reconcile job settles what's still pending.
    """

    expected = settings.mpesa_callback_token
    secret = expected.get_secret_value() if expected else ""
    if not secret or not hmac.compare_digest(token.encode(), secret.encode()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    parsed = _parse_callback(body)
    if parsed is None:
        logger.warning("Unreadable M-Pesa callback ignored")
        return _ACCEPTED
    checkout_request_id, result = parsed
    await service.apply_result(checkout_request_id=checkout_request_id, result=result)
    return _ACCEPTED


def _parse_callback(body: dict[str, Any]) -> tuple[str, StkResult] | None:
    try:
        callback = body["Body"]["stkCallback"]
        checkout = str(callback["CheckoutRequestID"])
        code = int(callback["ResultCode"])
        desc = str(callback.get("ResultDesc", ""))
        items = {
            item.get("Name"): item.get("Value")
            for item in (callback.get("CallbackMetadata") or {}).get("Item", [])
            if isinstance(item, dict)
        }
        amount = items.get("Amount")
        receipt = items.get("MpesaReceiptNumber")
        return checkout, StkResult(
            result_code=code,
            result_desc=desc[:255],
            receipt=str(receipt)[:32] if receipt else None,
            amount=int(float(amount)) if amount is not None else None,
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def get_mpesa_accounts(
    settings: Annotated[Settings, Depends(get_settings)],
    members: MemberService,
) -> MpesaAccounts:
    return MpesaAccounts(session=members.session, settings=settings, members=members)


AccountsService = Annotated[MpesaAccounts, Depends(get_mpesa_accounts)]


@router.get("/mpesa-account", response_model=APIResponse[MpesaAccountData])
async def get_mpesa_account(
    gym_id: UUID, current_user: CurrentUser, accounts: AccountsService
) -> APIResponse[MpesaAccountData]:
    """The gym's M-Pesa till (never the passkey)."""

    data = await accounts.get(user_id=current_user.id, gym_id=gym_id)
    return APIResponse(data=data)


@router.put("/mpesa-account", response_model=APIResponse[MpesaAccountData])
async def save_mpesa_account(
    gym_id: UUID,
    payload: SaveMpesaAccountRequest,
    current_user: CurrentUser,
    accounts: AccountsService,
) -> APIResponse[MpesaAccountData]:
    """Set where the gym's M-Pesa payments go. Owner only."""

    data = await accounts.save(user_id=current_user.id, gym_id=gym_id, payload=payload)
    return APIResponse(data=data)
