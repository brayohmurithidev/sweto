from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.profiles.enums import (
    AccountRole,
    OnboardingStatus,
)
from app.modules.profiles.exceptions import (
    InvalidProfileUpdateError,
)
from app.modules.profiles.models import (
    UserAccountRole,
    UserProfile,
)
from app.modules.profiles.repository import (
    UserAccountRoleRepository,
    UserProfileRepository,
)
from app.modules.profiles.schemas import (
    AccountRoleData,
    AccountSetupData,
    OnboardingStatusData,
    ProfileData,
    UpdateProfileData,
    UpdateProfileRequest,
)


class ProfileService:
    """Application service for account and profile setup."""

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        self.session = session
        self.profile_repository = UserProfileRepository(session)
        self.role_repository = UserAccountRoleRepository(session)

    async def select_account_role(
        self,
        *,
        user_id: UUID,
        role: AccountRole,
    ) -> AccountSetupData:
        profile = await self.profile_repository.get_by_user_id(user_id)

        if profile is None:
            profile = UserProfile(
                user_id=user_id,
            )

            self.profile_repository.add(profile)
            await self.session.flush()

        existing_role = await self.role_repository.get_by_user_and_role(
            user_id=user_id,
            role=role,
        )

        await self.role_repository.clear_default_roles(user_id)

        if existing_role is None:
            existing_role = UserAccountRole(
                user_id=user_id,
                role=role,
                is_active=True,
                is_default=True,
            )

            self.role_repository.add(existing_role)
            await self.session.flush()
        else:
            existing_role.is_active = True
            existing_role.is_default = True

        if role == AccountRole.GYM_OWNER:
            profile.onboarding_status = OnboardingStatus.GYM_SETUP_PENDING
            next_step = "gym_setup"
        else:
            profile.onboarding_status = OnboardingStatus.PROFILE_SETUP_PENDING
            next_step = "member_profile_setup"

        profile.onboarding_completed = False

        await self.session.commit()

        roles = await self.role_repository.list_for_user(user_id)

        return AccountSetupData(
            roles=[
                AccountRoleData(
                    id=item.id,
                    role=item.role,
                    is_active=item.is_active,
                    is_default=item.is_default,
                )
                for item in roles
            ],
            default_role=role,
            onboarding_status=profile.onboarding_status,
            onboarding_completed=profile.onboarding_completed,
            next_step=next_step,
        )

    async def get_onboarding_status(
        self,
        *,
        user_id: UUID,
    ) -> OnboardingStatusData:
        profile = await self.profile_repository.get_by_user_id(user_id)

        roles = await self.role_repository.list_for_user(user_id)

        active_roles = [item for item in roles if item.is_active]

        default_role = next(
            (item.role for item in active_roles if item.is_default),
            None,
        )

        if profile is None:
            return OnboardingStatusData(
                roles=[item.role for item in active_roles],
                default_role=default_role,
                onboarding_status=(OnboardingStatus.ACCOUNT_SELECTION_PENDING),
                onboarding_completed=False,
                next_step="choose_account",
            )

        return OnboardingStatusData(
            roles=[item.role for item in active_roles],
            default_role=default_role,
            onboarding_status=profile.onboarding_status,
            onboarding_completed=profile.onboarding_completed,
            next_step=self._resolve_next_step(profile.onboarding_status),
        )

    async def get_profile(
        self,
        *,
        user: User,
    ) -> ProfileData:
        profile = await self.profile_repository.get_by_user_id(user.id)

        if profile is None:
            profile = UserProfile(
                user_id=user.id,
            )

            self.profile_repository.add(profile)
            await self.session.commit()
            await self.session.refresh(profile)

        return self._build_profile_data(
            profile=profile,
            user=user,
        )

    async def update_profile(
        self,
        *,
        user: User,
        payload: UpdateProfileRequest,
    ) -> UpdateProfileData:
        profile = await self.profile_repository.get_by_user_id_for_update(user.id)

        if profile is None:
            profile = UserProfile(
                user_id=user.id,
            )

            self.profile_repository.add(profile)
            await self.session.flush()

        update_data = payload.model_dump(
            exclude_unset=True,
        )

        if "date_of_birth" in update_data:
            self._validate_date_of_birth(update_data["date_of_birth"])

        if "country_code" in update_data:
            country_code = update_data["country_code"]

            if country_code is not None:
                update_data["country_code"] = country_code.upper()

        for field_name, value in update_data.items():
            setattr(profile, field_name, value)

        default_role = await self.role_repository.get_default_for_user(user.id)

        if default_role is not None:
            if default_role.role == AccountRole.MEMBER:
                if self._is_member_profile_complete(profile):
                    profile.onboarding_status = OnboardingStatus.COMPLETED
                    profile.onboarding_completed = True
                else:
                    profile.onboarding_status = OnboardingStatus.PROFILE_SETUP_PENDING
                    profile.onboarding_completed = False

            elif default_role.role == AccountRole.GYM_OWNER:
                # Personal profile completion should not skip
                # the gym registration workflow.
                profile.onboarding_status = OnboardingStatus.GYM_SETUP_PENDING
                profile.onboarding_completed = False

        await self.session.commit()
        await self.session.refresh(profile)

        return UpdateProfileData(
            profile=self._build_profile_data(
                profile=profile,
                user=user,
            ),
            next_step=self._resolve_next_step(profile.onboarding_status),
        )

    @staticmethod
    def _build_profile_data(
        *,
        profile: UserProfile,
        user: User,
    ) -> ProfileData:
        return ProfileData(
            id=profile.id,
            user_id=profile.user_id,
            phone_number=user.phone_number,
            full_name=profile.full_name,
            email=profile.email,
            avatar_url=profile.avatar_url,
            neighbourhood=profile.neighbourhood,
            city=profile.city,
            country_code=profile.country_code,
            gender=profile.gender,
            date_of_birth=profile.date_of_birth,
            onboarding_status=profile.onboarding_status,
            onboarding_completed=profile.onboarding_completed,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    @staticmethod
    def _validate_date_of_birth(
        value: date | None,
    ) -> None:
        if value is None:
            return

        today = datetime.now(UTC).date()

        if value >= today:
            raise InvalidProfileUpdateError("Date of birth must be in the past.")

        oldest_allowed = date(
            today.year - 120,
            today.month,
            today.day,
        )

        if value < oldest_allowed:
            raise InvalidProfileUpdateError("Enter a valid date of birth.")

    @staticmethod
    def _is_member_profile_complete(
        profile: UserProfile,
    ) -> bool:
        return all(
            [
                profile.full_name,
                profile.neighbourhood,
                profile.city,
                profile.country_code,
            ]
        )

    @staticmethod
    def _resolve_next_step(
        status: OnboardingStatus,
    ) -> str:
        mapping = {
            OnboardingStatus.ACCOUNT_SELECTION_PENDING: ("choose_account"),
            OnboardingStatus.PROFILE_SETUP_PENDING: ("member_profile_setup"),
            OnboardingStatus.GYM_SETUP_PENDING: "gym_setup",
            OnboardingStatus.VERIFICATION_PENDING: ("verification_pending"),
            OnboardingStatus.COMPLETED: "dashboard",
        }

        return mapping[status]
