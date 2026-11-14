"""Settle M-Pesa payments whose callback never arrived.

    uv run python -m app.jobs.mpesa_reconcile

Run it every few minutes. For each STK Push still pending after a minute, it
asks Daraja for the result and settles the payment exactly as the callback
would (both go through MpesaPaymentService.apply_result, so a late callback
and this job can't both count it). A prompt with no answer after
MPESA_PENDING_TIMEOUT_MINUTES is given up as timed out.
"""

import asyncio
import logging
from collections import Counter
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.database.models  # noqa: F401  (registers every model for the mappers)
from app.core.config import Settings
from app.integrations.mpesa.base import MpesaError, MpesaGateway, StkResult
from app.integrations.sms.base import SMSProvider
from app.modules.members.enums import PaymentTransactionStatus
from app.modules.members.models import PaymentTransaction
from app.modules.members.mpesa_service import MpesaPaymentService
from app.modules.members.notifier import MemberNotifier
from app.modules.members.service import GymMemberService
from app.shared.clock import Clock

logger = logging.getLogger(__name__)

QUERY_AFTER = timedelta(minutes=1)
TIMED_OUT = StkResult(result_code=1037, result_desc="no_answer")


async def reconcile_pending(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    gateway: MpesaGateway,
    sms: SMSProvider,
    settings: Settings,
    clock: Clock,
) -> Counter[str]:
    outcomes: Counter[str] = Counter()
    now = clock()
    give_up_before = now - timedelta(minutes=settings.mpesa_pending_timeout_minutes)
    async with session_factory() as session:
        pending = (
            await session.execute(
                select(
                    PaymentTransaction.id,
                    PaymentTransaction.checkout_request_id,
                    PaymentTransaction.requested_at,
                ).where(
                    PaymentTransaction.status == PaymentTransactionStatus.PENDING,
                    PaymentTransaction.requested_at < now - QUERY_AFTER,
                )
            )
        ).all()
    for transaction_id, checkout, requested_at in pending:
        async with session_factory() as session:
            service = _service(session, gateway, sms, settings, clock)
            if checkout is None:
                # The push never got an answer back; nothing to ask about.
                if requested_at < give_up_before:
                    await _give_up(session, transaction_id, service)
                    outcomes["timed_out"] += 1
                continue
            try:
                result = await gateway.stk_query(checkout_request_id=checkout)
            except MpesaError as error:
                logger.warning("M-Pesa status query failed: reason=%s", error.reason)
                outcomes["query_failed"] += 1
                continue
            if result is None:
                if requested_at < give_up_before:
                    await service.apply_result(
                        checkout_request_id=checkout, result=TIMED_OUT
                    )
                    outcomes["timed_out"] += 1
                else:
                    outcomes["still_waiting"] += 1
                continue
            await service.apply_result(checkout_request_id=checkout, result=result)
            outcomes["paid" if result.succeeded else "failed"] += 1
    return outcomes


async def _give_up(
    session: AsyncSession, transaction_id: object, service: MpesaPaymentService
) -> None:
    transaction = await session.get(
        PaymentTransaction, transaction_id, with_for_update=True
    )
    if transaction is None or transaction.status != PaymentTransactionStatus.PENDING:
        return
    # Give it a placeholder ID so the shared settle path can find it.
    transaction.checkout_request_id = f"none-{transaction.id}"
    await session.commit()
    await service.apply_result(
        checkout_request_id=transaction.checkout_request_id, result=TIMED_OUT
    )


def _service(
    session: AsyncSession,
    gateway: MpesaGateway,
    sms: SMSProvider,
    settings: Settings,
    clock: Clock,
) -> MpesaPaymentService:
    members = GymMemberService(
        session=session,
        clock=clock,
        notifier=MemberNotifier(
            session=session,
            sms=sms,
            clock=clock,
            timeout_seconds=settings.sms_send_timeout_seconds,
        ),
        code_secret=settings.otp_hash_secret,
    )
    return MpesaPaymentService(
        session=session,
        clock=clock,
        settings=settings,
        gateway=gateway,
        members=members,
    )


async def _main() -> None:
    from app.core.config import get_settings
    from app.database.session import async_session_factory
    from app.integrations.mpesa.dependencies import build_mpesa_gateway
    from app.integrations.sms.dependencies import get_sms_provider
    from app.shared.clock import utc_now

    settings = get_settings()
    gateway = build_mpesa_gateway(settings)
    if gateway is None:
        logger.warning("M-Pesa reconcile: MPESA_MODE=disabled, nothing to do")
        return
    outcomes = await reconcile_pending(
        session_factory=async_session_factory,
        gateway=gateway,
        sms=get_sms_provider(),
        settings=settings,
        clock=utc_now,
    )
    logger.warning("M-Pesa reconcile: %s", dict(outcomes) or "nothing pending")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
