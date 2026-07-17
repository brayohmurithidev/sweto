from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.enums import (
    OTPPurpose,
    OTPStatus,
    SessionStatus,
)
from app.modules.auth.models import (
    OTPChallenge,
    RefreshSession,
    User,
)


class OTPChallengeRepository:
    """Database operations for OTP challenges."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest_pending(
        self,
        *,
        phone_number: str,
        purpose: OTPPurpose,
    ) -> OTPChallenge | None:
        statement = (
            select(OTPChallenge)
            .where(
                OTPChallenge.phone_number == phone_number,
                OTPChallenge.purpose == purpose,
                OTPChallenge.status == OTPStatus.PENDING,
            )
            .order_by(OTPChallenge.created_at.desc())
            .limit(1)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self,
        *,
        challenge_id: UUID,
    ) -> OTPChallenge | None:
        statement = (
            select(OTPChallenge)
            .where(OTPChallenge.id == challenge_id)
            .with_for_update()
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def expire_pending_challenges(
        self,
        *,
        phone_number: str,
        purpose: OTPPurpose,
        now: datetime,
    ) -> None:
        statement = (
            update(OTPChallenge)
            .where(
                OTPChallenge.phone_number == phone_number,
                OTPChallenge.purpose == purpose,
                OTPChallenge.status == OTPStatus.PENDING,
            )
            .values(
                status=OTPStatus.EXPIRED,
                updated_at=now,
            )
        )

        await self.session.execute(statement)

    def add(self, challenge: OTPChallenge) -> None:
        self.session.add(challenge)


class UserRepository:
    """Database operations for authenticatable users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_phone_number(
        self,
        phone_number: str,
    ) -> User | None:
        statement = select(User).where(User.phone_number == phone_number)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    def add(self, user: User) -> None:
        self.session.add(user)

    async def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        statement = select(User).where(User.id == user_id)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()


class RefreshSessionRepository:
    """Database operations for refresh sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_token_hash_for_update(
        self,
        token_hash: str,
    ) -> RefreshSession | None:
        statement = (
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_hash)
            .with_for_update()
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_active_by_id(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
    ) -> RefreshSession | None:
        statement = select(RefreshSession).where(
            RefreshSession.id == session_id,
            RefreshSession.user_id == user_id,
            RefreshSession.status == SessionStatus.ACTIVE,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    def add(
        self,
        refresh_session: RefreshSession,
    ) -> None:
        self.session.add(refresh_session)

    async def list_active_for_user(
        self,
        user_id: UUID,
    ) -> list[RefreshSession]:
        """Return active sessions belonging to a user."""

        statement = (
            select(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.status == SessionStatus.ACTIVE,
            )
            .order_by(RefreshSession.last_used_at.desc().nullslast())
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def get_by_id_for_update(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
    ) -> RefreshSession | None:
        """Lock and return a session belonging to a user."""

        statement = (
            select(RefreshSession)
            .where(
                RefreshSession.id == session_id,
                RefreshSession.user_id == user_id,
            )
            .with_for_update()
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def revoke_all_for_user(
        self,
        *,
        user_id: UUID,
        now: datetime,
        exclude_session_id: UUID | None = None,
    ) -> int:
        """Revoke active sessions belonging to a user."""

        conditions = [
            RefreshSession.user_id == user_id,
            RefreshSession.status == SessionStatus.ACTIVE,
        ]

        if exclude_session_id is not None:
            conditions.append(RefreshSession.id != exclude_session_id)

        statement = (
            update(RefreshSession)
            .where(*conditions)
            .values(
                status=SessionStatus.REVOKED,
                revoked_at=now,
                last_used_at=now,
                updated_at=now,
            )
            .returning(RefreshSession.id)
        )

        result = await self.session.execute(statement)
        revoked_session_ids = result.scalars().all()

        return len(revoked_session_ids)

    async def touch_session_if_stale(
        self,
        *,
        session_id: UUID,
        now: datetime,
        stale_before: datetime,
    ) -> None:
        """Update session activity only when its current value is stale."""

        statement = (
            update(RefreshSession)
            .where(
                RefreshSession.id == session_id,
                RefreshSession.status == SessionStatus.ACTIVE,
                (
                    RefreshSession.last_used_at.is_(None)
                    | (RefreshSession.last_used_at <= stale_before)
                ),
            )
            .values(
                last_used_at=now,
                updated_at=now,
            )
        )

        await self.session.execute(statement)
