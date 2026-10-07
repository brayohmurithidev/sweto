from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.profiles.enums import AccountRole
from app.modules.profiles.models import (
    UserAccountRole,
    UserProfile,
)


class UserProfileRepository:
    """Database operations for SWETO user profiles."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> UserProfile | None:
        statement = select(UserProfile).where(UserProfile.user_id == user_id)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_user_id_for_update(
        self,
        user_id: UUID,
    ) -> UserProfile | None:
        statement = (
            select(UserProfile).where(UserProfile.user_id == user_id).with_for_update()
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    def add(self, profile: UserProfile) -> None:
        self.session.add(profile)


class UserAccountRoleRepository:
    """Database operations for user account roles."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_and_role(
        self,
        *,
        user_id: UUID,
        role: AccountRole,
    ) -> UserAccountRole | None:
        statement = select(UserAccountRole).where(
            UserAccountRole.user_id == user_id,
            UserAccountRole.role == role,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
    ) -> list[UserAccountRole]:
        statement = (
            select(UserAccountRole)
            .where(UserAccountRole.user_id == user_id)
            .order_by(UserAccountRole.created_at.asc())
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def get_default_for_user(
        self,
        user_id: UUID,
    ) -> UserAccountRole | None:
        statement = select(UserAccountRole).where(
            UserAccountRole.user_id == user_id,
            UserAccountRole.is_active.is_(True),
            UserAccountRole.is_default.is_(True),
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def clear_default_roles(
        self,
        user_id: UUID,
    ) -> None:
        statement = (
            update(UserAccountRole)
            .where(
                UserAccountRole.user_id == user_id,
                UserAccountRole.is_default.is_(True),
            )
            .values(is_default=False)
        )

        await self.session.execute(statement)

    def add(self, account_role: UserAccountRole) -> None:
        self.session.add(account_role)
