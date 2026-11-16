"""Each gym's own M-Pesa till, and choosing the account a prompt uses."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.integrations.mpesa.base import MpesaAccount
from app.integrations.mpesa.credentials import PasskeyCipher
from app.integrations.mpesa.dependencies import default_mpesa_account
from app.modules.gyms.permissions import GymPermission
from app.modules.members.exceptions import (
    InvalidMembershipPaymentError,
    MpesaNotConfiguredError,
)
from app.modules.members.models import GymMpesaAccount
from app.modules.members.schemas import MpesaAccountData, SaveMpesaAccountRequest
from app.modules.members.service import GymMemberService

TRANSACTION_TYPES = {
    "paybill": "CustomerPayBillOnline",
    "till": "CustomerBuyGoodsOnline",
}


class MpesaAccounts:
    def __init__(
        self, *, session: AsyncSession, settings: Settings, members: GymMemberService
    ) -> None:
        self.session = session
        self.settings = settings
        self.members = members

    async def get(self, *, user_id: UUID, gym_id: UUID) -> MpesaAccountData:
        gym = await self.members._gym_for(
            user_id=user_id, gym_id=gym_id, permission=GymPermission.TAKE_PAYMENTS
        )
        return self._data(await self._row(gym.id))

    async def save(
        self, *, user_id: UUID, gym_id: UUID, payload: SaveMpesaAccountRequest
    ) -> MpesaAccountData:
        """Only the gym's owner sets where its money goes."""

        await self.members._gym_for(
            user_id=user_id,
            gym_id=gym_id,
            permission=GymPermission.MANAGE_PAYMENT_SETTINGS,
        )
        cipher = self._cipher()
        row = await self._row(gym_id)
        if row is None and payload.passkey is None:
            raise InvalidMembershipPaymentError(
                "Enter the passkey Safaricom gave you for this shortcode."
            )
        if row is None:
            row = GymMpesaAccount(gym_id=gym_id)
            self.session.add(row)
        row.account_type = payload.account_type
        row.shortcode = payload.shortcode
        row.party_b = (
            payload.till_number
            if payload.account_type == "till" and payload.till_number
            else payload.shortcode
        )
        if payload.passkey is not None:
            row.passkey_encrypted = cipher.encrypt(payload.passkey.strip())
        row.updated_by_user_id = user_id
        await self.session.commit()
        await self.session.refresh(row)
        return self._data(row)

    async def for_gym(self, gym_id: UUID) -> MpesaAccount:
        """The account a prompt for this gym is sent from."""

        row = await self._row(gym_id)
        if row is not None:
            return MpesaAccount(
                shortcode=row.shortcode,
                passkey=self._cipher().decrypt(row.passkey_encrypted),
                transaction_type=TRANSACTION_TYPES[row.account_type],
                party_b=row.party_b,
            )
        fallback = default_mpesa_account(self.settings)
        if fallback is None:
            raise MpesaNotConfiguredError(
                "Add your M-Pesa till first: More → M-Pesa till."
            )
        return fallback

    def _cipher(self) -> PasskeyCipher:
        key = self.settings.mpesa_credentials_key
        if key is None or not key.get_secret_value():
            raise MpesaNotConfiguredError(
                "This server can't store M-Pesa tills yet (no credentials key)."
            )
        return PasskeyCipher(key.get_secret_value())

    async def _row(self, gym_id: UUID) -> GymMpesaAccount | None:
        found: GymMpesaAccount | None = await self.session.scalar(
            select(GymMpesaAccount).where(GymMpesaAccount.gym_id == gym_id)
        )
        return found

    def _data(self, row: GymMpesaAccount | None) -> MpesaAccountData:
        if row is None:
            return MpesaAccountData(configured=False, mode=self.settings.mpesa_mode)
        return MpesaAccountData(
            configured=True,
            account_type=row.account_type,
            shortcode=row.shortcode,
            till_number=row.party_b if row.account_type == "till" else None,
            passkey_saved=True,
            updated_at=row.updated_at,
            mode=self.settings.mpesa_mode,
        )
