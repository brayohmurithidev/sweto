"""Membership renewals paid by M-Pesa STK Push.

Requesting a payment creates the membership period as pending_payment, a
pending Payment and a PaymentTransaction for the STK Push. Nothing counts as
paid until M-Pesa confirms: by callback, or by a status query from the
reconcile job when the callback never arrives. Both go through
``apply_result``, which locks the transaction row and ignores anything but
the first final answer, so duplicates and races are harmless. The period's
dates are fixed when the money arrives, by the gym's calendar, so paying a
day late never loses or invents days.
"""

import asyncio
import logging
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.integrations.mpesa.base import (
    MpesaError,
    MpesaGateway,
    StkResult,
    result_message,
)
from app.modules.gyms.enums import MembershipBillingPeriod
from app.modules.gyms.models import Gym
from app.modules.members.enums import (
    GymMembershipStatus,
    GymMemberStatus,
    MemberMessageStatus,
    PaymentMethod,
    PaymentStatus,
    PaymentTransactionStatus,
)
from app.modules.members.exceptions import (
    GymMemberArchivedError,
    InvalidMembershipPaymentError,
    MpesaNotConfiguredError,
    MpesaPaymentPendingError,
    MpesaRequestFailedError,
    PaymentNotFoundError,
)
from app.modules.members.models import (
    GymMember,
    GymMembership,
    Payment,
    PaymentTransaction,
)
from app.modules.members.mpesa_accounts import MpesaAccounts
from app.modules.members.periods import period_end
from app.modules.members.schemas import MpesaPaymentData, RequestMpesaPaymentRequest
from app.modules.members.service import GymMemberService
from app.shared.clock import Clock

logger = logging.getLogger(__name__)

PROVIDER = "mpesa"
# A second prompt while the first may still be on the member's phone would
# risk two payments.
PENDING_GUARD = timedelta(minutes=3)


class MpesaPaymentService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        clock: Clock,
        settings: Settings,
        gateway: MpesaGateway | None,
        members: GymMemberService,
    ) -> None:
        self.session = session
        self.clock = clock
        self.settings = settings
        self.gateway = gateway
        self.members = members

    async def request(
        self,
        *,
        user_id: UUID,
        gym_id: UUID,
        member_id: UUID,
        payload: RequestMpesaPaymentRequest,
    ) -> MpesaPaymentData:
        if self.gateway is None:
            raise MpesaNotConfiguredError(
                "M-Pesa payments aren't switched on yet. Record cash for now."
            )
        gym = await self.members._gym_for_manager(user_id=user_id, gym_id=gym_id)
        member = await self.members._member(gym, member_id, for_update=True)
        if member.status == GymMemberStatus.ARCHIVED:
            raise GymMemberArchivedError(
                "This member is archived. Restore them before requesting a payment."
            )
        plan = await self.members.plans.get(gym_id=gym.id, plan_id=payload.plan_id)
        if plan is None or not plan.is_active:
            raise InvalidMembershipPaymentError(
                "That membership plan isn't available. Choose an active plan."
            )
        if plan.currency != "KES":
            raise InvalidMembershipPaymentError("M-Pesa payments must be in KES.")
        amount = payload.amount or int(plan.amount)
        if Decimal(amount) != plan.amount and payload.amount is None:
            raise InvalidMembershipPaymentError(
                "This plan's price has cents; enter a whole-shilling amount."
            )
        phone = (
            self.members._normalize_phone(payload.phone_number, gym)
            if payload.phone_number
            else member.phone_number
        )
        account = await MpesaAccounts(
            session=self.session, settings=self.settings, members=self.members
        ).for_gym(gym.id)
        now = self.clock()
        await self._guard_pending(member.id)

        today = self.members._today(gym)
        billing_period = MembershipBillingPeriod(plan.billing_period)
        membership = GymMembership(
            gym_id=gym.id,
            member_id=member.id,
            plan_id=plan.id,
            plan_name=plan.name,
            amount=Decimal(amount),
            currency=plan.currency,
            billing_period=billing_period,
            # Provisional: fixed when M-Pesa confirms the money.
            starts_on=today,
            ends_on=period_end(today, billing_period),
            status=GymMembershipStatus.PENDING_PAYMENT,
            visit_limit=plan.visit_limit,
        )
        self.session.add(membership)
        await self.session.flush()
        payment = Payment(
            gym_id=gym.id,
            membership_id=membership.id,
            amount=Decimal(amount),
            currency=plan.currency,
            method=PaymentMethod.MPESA,
            status=PaymentStatus.PENDING,
            payer_phone=phone,
            recorded_by_user_id=user_id,
        )
        self.session.add(payment)
        await self.session.flush()
        transaction = PaymentTransaction(
            payment_id=payment.id,
            gym_id=gym.id,
            provider=PROVIDER,
            amount=Decimal(amount),
            status=PaymentTransactionStatus.PENDING,
            requested_at=now,
        )
        self.session.add(transaction)
        await self.session.commit()

        try:
            async with asyncio.timeout(self.settings.mpesa_timeout_seconds + 5):
                accepted = await self.gateway.stk_push(
                    account=account,
                    phone_number=phone,
                    amount=amount,
                    account_reference=gym.name.replace(" ", "")[:12] or "SWETO",
                    description="Membership",
                    callback_url=self._callback_url(),
                )
        except (MpesaError, TimeoutError) as error:
            reason = error.reason if isinstance(error, MpesaError) else "timeout"
            unknown = isinstance(error, TimeoutError) or (
                isinstance(error, MpesaError) and error.outcome_unknown
            )
            await self._fail(payment, membership, transaction, None, reason)
            raise MpesaRequestFailedError(
                "M-Pesa didn't answer. Ask the member whether a prompt appeared "
                "before trying again."
                if unknown
                else "M-Pesa couldn't send the prompt. Check the number and try "
                "again, or record cash."
            ) from error
        transaction.merchant_request_id = accepted.merchant_request_id
        transaction.checkout_request_id = accepted.checkout_request_id
        await self.session.commit()
        return await self._data(payment, None)

    async def status(
        self, *, user_id: UUID, gym_id: UUID, payment_id: UUID
    ) -> MpesaPaymentData:
        gym = await self.members._gym_for_manager(user_id=user_id, gym_id=gym_id)
        payment = await self.session.scalar(
            select(Payment).where(Payment.id == payment_id, Payment.gym_id == gym.id)
        )
        if payment is None:
            raise PaymentNotFoundError("This payment was not found in your gym.")
        return await self._data(payment, None)

    async def apply_result(
        self, *, checkout_request_id: str, result: StkResult
    ) -> MemberMessageStatus | None:
        """Settle a pending STK Push once; later answers are ignored."""

        transaction = await self.session.scalar(
            select(PaymentTransaction)
            .where(PaymentTransaction.checkout_request_id == checkout_request_id)
            .with_for_update()
        )
        if transaction is None:
            logger.warning("M-Pesa result for an unknown checkout request")
            return None
        if transaction.status != PaymentTransactionStatus.PENDING:
            await self.session.rollback()
            return None
        payment = await self.session.get(Payment, transaction.payment_id)
        assert payment is not None
        membership = await self.session.get(GymMembership, payment.membership_id)
        assert membership is not None

        if result.succeeded and (
            result.amount is not None and Decimal(result.amount) != payment.amount
        ):
            # Paid, but not what we asked for: don't activate on our own;
            # staff sort it out with the member.
            logger.warning("M-Pesa amount mismatch on a payment")
            await self._fail(
                payment, membership, transaction, result.result_code, "amount_mismatch"
            )
            transaction.provider_receipt = result.receipt
            await self.session.commit()
            return None
        if not result.succeeded:
            await self._fail(
                payment,
                membership,
                transaction,
                result.result_code,
                result.result_desc[:255] or "declined",
            )
            return None

        gym = await self.session.get(Gym, payment.gym_id)
        member = await self.session.get(GymMember, membership.member_id)
        assert gym is not None and member is not None
        await self.session.refresh(member, with_for_update=True)
        today = self.members._today(gym)
        paid_until = await self.members.members.paid_until(member.id)
        starts_on = today
        if paid_until is not None and paid_until >= today:
            starts_on = paid_until + timedelta(days=1)
        billing_period = MembershipBillingPeriod(membership.billing_period)
        membership.starts_on = starts_on
        membership.ends_on = period_end(starts_on, billing_period)
        membership.status = GymMembershipStatus.ACTIVE
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = self.clock()
        transaction.status = PaymentTransactionStatus.SUCCEEDED
        transaction.result_code = 0
        transaction.result_reason = "paid"
        transaction.provider_receipt = result.receipt
        transaction.completed_at = self.clock()
        await self.session.commit()
        return await self.members.notify_payment(gym, member, membership)

    async def _fail(
        self,
        payment: Payment,
        membership: GymMembership,
        transaction: PaymentTransaction,
        result_code: int | None,
        reason: str,
    ) -> None:
        payment.status = PaymentStatus.FAILED
        membership.status = GymMembershipStatus.CANCELLED
        transaction.status = PaymentTransactionStatus.FAILED
        transaction.result_code = result_code
        transaction.result_reason = reason[:255]
        transaction.completed_at = self.clock()
        await self.session.commit()

    async def _guard_pending(self, member_id: UUID) -> None:
        recent = await self.session.scalar(
            select(PaymentTransaction.id)
            .join(Payment, Payment.id == PaymentTransaction.payment_id)
            .join(GymMembership, GymMembership.id == Payment.membership_id)
            .where(
                GymMembership.member_id == member_id,
                PaymentTransaction.status == PaymentTransactionStatus.PENDING,
                PaymentTransaction.requested_at > self.clock() - PENDING_GUARD,
            )
            .limit(1)
        )
        if recent is not None:
            raise MpesaPaymentPendingError(
                "An M-Pesa prompt for this member is still waiting. Give them a "
                "minute to answer it before sending another."
            )

    def _callback_url(self) -> str:
        base = (
            self.settings.mpesa_callback_base_url or "http://localhost:8000"
        ).rstrip("/")
        token = self.settings.mpesa_callback_token
        secret = token.get_secret_value() if token else "local"
        return f"{base}{self.settings.api_v1_prefix}/payments/mpesa/callback/{secret}"

    async def _data(
        self, payment: Payment, sms: MemberMessageStatus | None
    ) -> MpesaPaymentData:
        membership = await self.session.get(GymMembership, payment.membership_id)
        assert membership is not None
        transaction = await self.session.scalar(
            select(PaymentTransaction)
            .where(PaymentTransaction.payment_id == payment.id)
            .order_by(PaymentTransaction.requested_at.desc())
            .limit(1)
        )
        if payment.status == PaymentStatus.COMPLETED:
            message = "Paid."
        elif payment.status == PaymentStatus.PENDING:
            message = "Waiting for the member to enter their M-Pesa PIN."
        elif transaction is not None and transaction.result_reason == "amount_mismatch":
            message = (
                "M-Pesa received a different amount than requested. Check the "
                "member's M-Pesa message and record the payment by hand."
            )
        else:
            message = result_message(transaction.result_code if transaction else None)
        return MpesaPaymentData(
            payment_id=payment.id,
            member_id=membership.member_id,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            plan_name=membership.plan_name,
            message=message,
            receipt=transaction.provider_receipt if transaction else None,
            paid_until=membership.ends_on
            if payment.status == PaymentStatus.COMPLETED
            else None,
            sms=sms,
        )
