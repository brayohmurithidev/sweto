"""Local stand-in for M-Pesa: accepts every request, never takes money.

The result arrives only when you post a callback yourself (see
docs/mpesa.md), exactly as Safaricom would.
"""

import logging
import uuid

from app.integrations.mpesa.base import StkPushAccepted, StkResult

logger = logging.getLogger(__name__)


class SimulatedMpesaGateway:
    async def stk_push(
        self,
        *,
        phone_number: str,
        amount: int,
        account_reference: str,
        description: str,
        callback_url: str,
    ) -> StkPushAccepted:
        checkout = f"ws_CO_SIM_{uuid.uuid4().hex[:20]}"
        logger.warning(
            "SWETO SIMULATED M-PESA | amount=%s checkout=%s (post a callback "
            "to complete it)",
            amount,
            checkout,
        )
        return StkPushAccepted(
            merchant_request_id=f"SIM-{uuid.uuid4().hex[:12]}",
            checkout_request_id=checkout,
        )

    async def stk_query(self, *, checkout_request_id: str) -> StkResult | None:
        return None
