from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.exceptions import (
    AdminEmailAlreadyExistsError,
    AdminNotFoundError,
    InvalidAdminRoleChangeError,
    InvalidAdminStatusError,
    ProtectedSystemUserError,
    SelfAdministrationNotAllowedError,
    SuperAdminConfigurationError,
    SuperAdminIntegrityError,
)
from app.modules.admin.schemas import AdminUserData, AdminUserListData
from app.modules.auth.audit import AuthAuditLogger
from app.modules.auth.enums import (
    AuthEventOutcome,
    AuthEventType,
    UserRole,
    UserStatus,
)
from app.modules.auth.exceptions import PasswordPolicyViolationError
from app.modules.auth.models import User
from app.modules.auth.repository import RefreshSessionRepository, UserRepository
from app.modules.auth.security import (
    hash_password,
    normalize_email,
    validate_password_policy,
)


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    user: User
    created: bool


class AdminService:
    """Domain service for the protected Super Admin and normal Admins."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)
        self.session_repository = RefreshSessionRepository(session)
        self.audit_logger = AuthAuditLogger(session)

    @staticmethod
    def _build_user_data(user: User) -> AdminUserData:
        return AdminUserData(
            id=user.id,
            email=user.email,
            phone_number=user.phone_number,
            role=user.role,
            status=user.status,
            must_change_password=user.must_change_password,
            is_system_protected=user.is_system_protected,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    def _ensure_mutable(user: User) -> None:
        if user.is_system_protected or user.role == UserRole.SUPER_ADMIN:
            raise ProtectedSystemUserError(
                "The protected system Super Admin cannot be modified."
            )

    @staticmethod
    def _ensure_super_admin_actor(actor: User) -> None:
        if actor.role != UserRole.SUPER_ADMIN:
            raise InvalidAdminRoleChangeError(
                "Only the Super Admin may manage platform administrators."
            )

    @staticmethod
    def _ensure_not_self(*, actor_id: UUID, target: User) -> None:
        if actor_id == target.id:
            raise SelfAdministrationNotAllowedError(
                "You cannot perform this administrative action on yourself."
            )

    async def ensure_initial_super_admin(
        self, *, email: str | None, password: str | None
    ) -> BootstrapResult:
        if email is None or not email.strip():
            raise SuperAdminConfigurationError(
                "SWETO_SUPER_ADMIN_EMAIL is required for bootstrap."
            )
        if password is None or not password:
            raise SuperAdminConfigurationError(
                "SWETO_SUPER_ADMIN_PASSWORD is required for bootstrap."
            )
        try:
            validate_password_policy(password)
        except PasswordPolicyViolationError as exc:
            raise SuperAdminConfigurationError(str(exc)) from exc

        normalized_email = normalize_email(email)
        await self.user_repository.acquire_super_admin_bootstrap_lock()
        super_admins = await self.user_repository.get_super_admins(for_update=True)
        if len(super_admins) > 1:
            raise SuperAdminIntegrityError(
                "Multiple Super Admin accounts exist; manual resolution is required."
            )
        if super_admins:
            existing = super_admins[0]
            if not existing.is_system_protected:
                raise SuperAdminIntegrityError(
                    "The existing Super Admin is not system protected."
                )
            if existing.status != UserStatus.ACTIVE:
                raise SuperAdminIntegrityError(
                    "The protected Super Admin is not active."
                )
            if existing.email != normalized_email:
                raise SuperAdminIntegrityError(
                    "A protected Super Admin exists with a different email."
                )
            return BootstrapResult(user=existing, created=False)

        email_owner = await self.user_repository.get_by_email_for_update(
            normalized_email
        )
        if email_owner is not None:
            raise SuperAdminIntegrityError(
                "The configured email already belongs to another account."
            )

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            phone_number=None,
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            must_change_password=True,
            is_system_protected=True,
            is_phone_verified=False,
        )
        self.user_repository.add(user)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise SuperAdminIntegrityError(
                "Concurrent bootstrap conflict; inspect existing accounts and retry."
            ) from exc
        self.audit_logger.record(
            event_type=AuthEventType.SUPER_ADMIN_BOOTSTRAPPED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=user.id,
        )
        await self.session.commit()
        return BootstrapResult(user=user, created=True)

    async def create_admin(
        self, *, actor: User, email: str, temporary_password: str
    ) -> AdminUserData:
        self._ensure_super_admin_actor(actor)
        normalized_email = normalize_email(email)
        validate_password_policy(temporary_password)
        if await self.user_repository.get_by_email_for_update(normalized_email):
            raise AdminEmailAlreadyExistsError(
                "An account with this email already exists."
            )
        user = User(
            email=normalized_email,
            password_hash=hash_password(temporary_password),
            phone_number=None,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            must_change_password=True,
            is_system_protected=False,
            is_phone_verified=False,
        )
        self.user_repository.add(user)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AdminEmailAlreadyExistsError(
                "An account with this email already exists."
            ) from exc
        self.audit_logger.record(
            event_type=AuthEventType.ADMIN_CREATED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=actor.id,
            metadata={"created_user_id": str(user.id)},
        )
        await self.session.commit()
        await self.session.refresh(user)
        return self._build_user_data(user)

    async def list_admins(
        self, *, actor: User, limit: int, offset: int
    ) -> AdminUserListData:
        self._ensure_super_admin_actor(actor)
        users, total = await self.user_repository.list_platform_admins(
            limit=limit, offset=offset
        )
        return AdminUserListData(
            users=[self._build_user_data(user) for user in users],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_admin(self, *, actor: User, user_id: UUID) -> AdminUserData:
        self._ensure_super_admin_actor(actor)
        user = await self.user_repository.get_by_id(user_id)
        if user is None or user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise AdminNotFoundError("The requested administrator was not found.")
        return self._build_user_data(user)

    async def update_status(
        self, *, actor: User, user_id: UUID, status: UserStatus
    ) -> AdminUserData:
        self._ensure_super_admin_actor(actor)
        if status not in {
            UserStatus.ACTIVE,
            UserStatus.SUSPENDED,
            UserStatus.DEACTIVATED,
        }:
            raise InvalidAdminStatusError("The requested Admin status is invalid.")
        target = await self.user_repository.get_by_id_for_update(user_id)
        if target is None or target.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise AdminNotFoundError("The requested administrator was not found.")
        self._ensure_not_self(actor_id=actor.id, target=target)
        self._ensure_mutable(target)
        target.status = status
        revoked = 0
        if status in {UserStatus.SUSPENDED, UserStatus.DEACTIVATED}:
            revoked = await self.session_repository.revoke_all_for_user(
                user_id=target.id, now=datetime.now(UTC)
            )
        self.audit_logger.record(
            event_type=AuthEventType.ADMIN_STATUS_CHANGED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=actor.id,
            metadata={
                "target_user_id": str(target.id),
                "status": status.value,
                "sessions_revoked": revoked,
            },
        )
        await self.session.commit()
        await self.session.refresh(target)
        return self._build_user_data(target)

    async def demote_admin(self, *, actor: User, user_id: UUID) -> AdminUserData:
        self._ensure_super_admin_actor(actor)
        target = await self.user_repository.get_by_id_for_update(user_id)
        if target is None:
            raise AdminNotFoundError("The requested administrator was not found.")
        self._ensure_not_self(actor_id=actor.id, target=target)
        self._ensure_mutable(target)
        if target.role != UserRole.ADMIN:
            raise InvalidAdminRoleChangeError("Only an Admin may be demoted to User.")
        target.role = UserRole.USER
        target.must_change_password = False
        revoked = await self.session_repository.revoke_all_for_user(
            user_id=target.id, now=datetime.now(UTC)
        )
        self.audit_logger.record(
            event_type=AuthEventType.ADMIN_ROLE_CHANGED,
            outcome=AuthEventOutcome.SUCCESS,
            user_id=actor.id,
            metadata={
                "target_user_id": str(target.id),
                "role": UserRole.USER.value,
                "sessions_revoked": revoked,
            },
        )
        await self.session.commit()
        await self.session.refresh(target)
        return self._build_user_data(target)

    async def remove_protection(self, *, actor: User, user_id: UUID) -> None:
        """Defense-in-depth entry point; no route exposes this operation."""

        self._ensure_super_admin_actor(actor)
        target = await self.user_repository.get_by_id_for_update(user_id)
        if target is None:
            raise AdminNotFoundError("The requested administrator was not found.")
        self._ensure_not_self(actor_id=actor.id, target=target)
        self._ensure_mutable(target)
        raise InvalidAdminRoleChangeError("System protection cannot be changed.")

    async def delete_admin(self, *, actor: User, user_id: UUID) -> None:
        """Reject protected deletion; hard deletion is not supported."""

        self._ensure_super_admin_actor(actor)
        target = await self.user_repository.get_by_id_for_update(user_id)
        if target is None:
            raise AdminNotFoundError("The requested administrator was not found.")
        self._ensure_not_self(actor_id=actor.id, target=target)
        self._ensure_mutable(target)
        raise InvalidAdminStatusError(
            "Hard deletion is not supported; deactivate the Admin instead."
        )
