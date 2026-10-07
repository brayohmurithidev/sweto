from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.database import models  # noqa: F401
from app.modules.admin.dependencies import require_platform_roles
from app.modules.admin.exceptions import (
    AdminEmailAlreadyExistsError,
    InvalidAdminRoleChangeError,
    InvalidAdminStatusError,
    PlatformRoleRequiredError,
    ProtectedSystemUserError,
    SelfAdministrationNotAllowedError,
    SuperAdminConfigurationError,
    SuperAdminIntegrityError,
)
from app.modules.admin.service import AdminService
from app.modules.auth.dependencies import AuthContext
from app.modules.auth.enums import SessionStatus, UserRole, UserStatus
from app.modules.auth.exceptions import (
    PasswordChangeRequiredError,
    PasswordPolicyViolationError,
)
from app.modules.auth.models import RefreshSession, User
from app.modules.auth.security import hash_password, verify_password


def session_mock() -> Mock:
    session = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


def user(
    *,
    role: UserRole,
    email: str = "admin@example.com",
    status: UserStatus = UserStatus.ACTIVE,
    protected: bool = False,
    must_change_password: bool = False,
) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        email=email,
        password_hash=hash_password("temporary-password"),
        phone_number=None,
        role=role,
        status=status,
        must_change_password=must_change_password,
        is_system_protected=protected,
        is_phone_verified=False,
        created_at=now,
        updated_at=now,
    )


def service() -> AdminService:
    return AdminService(session_mock())


def configure_bootstrap(
    admin_service: AdminService,
    *,
    super_admins: list[User] | None = None,
    email_owner: User | None = None,
) -> list[User]:
    created: list[User] = []
    admin_service.user_repository.acquire_super_admin_bootstrap_lock = AsyncMock()
    admin_service.user_repository.get_super_admins = AsyncMock(
        return_value=super_admins or []
    )
    admin_service.user_repository.get_by_email_for_update = AsyncMock(
        return_value=email_owner
    )
    admin_service.user_repository.add = Mock(side_effect=created.append)
    return created


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email", "password"),
    [
        (None, "temporary-password"),
        ("", "temporary-password"),
        ("admin@example.com", None),
        ("admin@example.com", ""),
        ("admin@example.com", "weak"),
    ],
)
async def test_bootstrap_rejects_missing_or_weak_configuration(
    email: str | None, password: str | None
) -> None:
    with pytest.raises(SuperAdminConfigurationError):
        await service().ensure_initial_super_admin(email=email, password=password)


@pytest.mark.asyncio
async def test_bootstrap_creates_protected_super_admin() -> None:
    admin_service = service()
    created = configure_bootstrap(admin_service)

    result = await admin_service.ensure_initial_super_admin(
        email="  ROOT@Example.COM ", password="temporary-password"
    )

    assert result.created is True
    assert result.user is created[0]
    assert result.user.email == "root@example.com"
    assert result.user.role == UserRole.SUPER_ADMIN
    assert result.user.status == UserStatus.ACTIVE
    assert result.user.must_change_password is True
    assert result.user.is_system_protected is True
    assert result.user.phone_number is None
    assert result.user.password_hash != "temporary-password"
    assert verify_password("temporary-password", result.user.password_hash or "")


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent_and_does_not_reset_password() -> None:
    existing = user(
        role=UserRole.SUPER_ADMIN,
        email="root@example.com",
        protected=True,
    )
    original_hash = existing.password_hash
    admin_service = service()
    created = configure_bootstrap(admin_service, super_admins=[existing])

    result = await admin_service.ensure_initial_super_admin(
        email="ROOT@example.com", password="a-different-password"
    )

    assert result.created is False
    assert existing.password_hash == original_hash
    assert created == []


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.USER, UserRole.ADMIN])
async def test_bootstrap_does_not_promote_existing_account(role: UserRole) -> None:
    admin_service = service()
    configure_bootstrap(admin_service, email_owner=user(role=role))

    with pytest.raises(SuperAdminIntegrityError):
        await admin_service.ensure_initial_super_admin(
            email="admin@example.com", password="temporary-password"
        )


@pytest.mark.asyncio
async def test_bootstrap_rejects_other_email_multiple_or_invalid_super_admin() -> None:
    cases = [
        [user(role=UserRole.SUPER_ADMIN, email="other@example.com", protected=True)],
        [
            user(role=UserRole.SUPER_ADMIN, protected=True),
            user(role=UserRole.SUPER_ADMIN, email="other@example.com", protected=True),
        ],
        [user(role=UserRole.SUPER_ADMIN, protected=False)],
        [
            user(
                role=UserRole.SUPER_ADMIN,
                protected=True,
                status=UserStatus.SUSPENDED,
            )
        ],
    ]
    for super_admins in cases:
        admin_service = service()
        configure_bootstrap(admin_service, super_admins=super_admins)
        with pytest.raises(SuperAdminIntegrityError):
            await admin_service.ensure_initial_super_admin(
                email="admin@example.com", password="temporary-password"
            )


@pytest.mark.asyncio
async def test_bootstrap_handles_concurrent_integrity_failure() -> None:
    admin_service = service()
    configure_bootstrap(admin_service)
    admin_service.session.flush = AsyncMock(
        side_effect=IntegrityError("insert", {}, Exception("unique"))
    )

    with pytest.raises(SuperAdminIntegrityError):
        await admin_service.ensure_initial_super_admin(
            email="admin@example.com", password="temporary-password"
        )
    admin_service.session.rollback.assert_awaited_once()


def auth_context(account: User) -> AuthContext:
    return AuthContext(
        user=account,
        session=RefreshSession(
            id=uuid4(),
            user_id=account.id,
            token_hash="hash",
            status=SessionStatus.ACTIVE,
            expires_at=datetime.now(UTC),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.USER, UserRole.ADMIN])
async def test_platform_dependency_blocks_non_super_admin(role: UserRole) -> None:
    dependency = require_platform_roles(UserRole.SUPER_ADMIN)
    with pytest.raises(PlatformRoleRequiredError):
        await dependency(auth_context(user(role=role)))


@pytest.mark.asyncio
async def test_platform_dependency_allows_super_admin() -> None:
    account = user(role=UserRole.SUPER_ADMIN, protected=True)
    dependency = require_platform_roles(UserRole.SUPER_ADMIN)
    assert await dependency(auth_context(account)) is account


@pytest.mark.asyncio
async def test_password_gate_precedes_platform_role_check() -> None:
    from app.modules.auth.dependencies import require_password_change_complete

    account = user(role=UserRole.SUPER_ADMIN, protected=True, must_change_password=True)
    with pytest.raises(PasswordChangeRequiredError):
        await require_password_change_complete(auth_context(account))


@pytest.mark.asyncio
async def test_create_admin_is_safe_and_normalized() -> None:
    admin_service = service()
    actor = user(role=UserRole.SUPER_ADMIN, protected=True)
    created: list[User] = []
    admin_service.user_repository.get_by_email_for_update = AsyncMock(return_value=None)
    admin_service.user_repository.add = Mock(side_effect=created.append)

    async def populate_database_defaults() -> None:
        account = created[0]
        now = datetime.now(UTC)
        account.id = uuid4()
        account.created_at = now
        account.updated_at = now

    admin_service.session.flush = AsyncMock(side_effect=populate_database_defaults)

    result = await admin_service.create_admin(
        actor=actor,
        email=" NEW@Example.COM ",
        temporary_password="temporary-password",
    )

    account = created[0]
    assert result.email == "new@example.com"
    assert result.role == UserRole.ADMIN
    assert result.status == UserStatus.ACTIVE
    assert result.must_change_password is True
    assert result.is_system_protected is False
    assert account.password_hash != "temporary-password"
    assert "password_hash" not in result.model_dump()


@pytest.mark.asyncio
async def test_create_admin_rejects_duplicate_and_weak_password() -> None:
    actor = user(role=UserRole.SUPER_ADMIN, protected=True)
    admin_service = service()
    admin_service.user_repository.get_by_email_for_update = AsyncMock(
        return_value=user(role=UserRole.USER)
    )
    with pytest.raises(AdminEmailAlreadyExistsError):
        await admin_service.create_admin(
            actor=actor,
            email="admin@example.com",
            temporary_password="temporary-password",
        )
    with pytest.raises(PasswordPolicyViolationError, match="between 12 and 128"):
        await admin_service.create_admin(
            actor=actor, email="other@example.com", temporary_password="weak"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["status", "demote", "delete", "protect"])
async def test_protected_super_admin_cannot_be_modified(operation: str) -> None:
    actor = user(role=UserRole.SUPER_ADMIN, email="actor@example.com", protected=True)
    target = user(role=UserRole.SUPER_ADMIN, protected=True)
    admin_service = service()
    admin_service.user_repository.get_by_id_for_update = AsyncMock(return_value=target)
    with pytest.raises(ProtectedSystemUserError):
        if operation == "status":
            await admin_service.update_status(
                actor=actor, user_id=target.id, status=UserStatus.SUSPENDED
            )
        elif operation == "demote":
            await admin_service.demote_admin(actor=actor, user_id=target.id)
        elif operation == "delete":
            await admin_service.delete_admin(actor=actor, user_id=target.id)
        else:
            await admin_service.remove_protection(actor=actor, user_id=target.id)


@pytest.mark.asyncio
async def test_super_admin_cannot_manage_self_destructively() -> None:
    actor = user(role=UserRole.SUPER_ADMIN, protected=True)
    admin_service = service()
    admin_service.user_repository.get_by_id_for_update = AsyncMock(return_value=actor)
    with pytest.raises(SelfAdministrationNotAllowedError):
        await admin_service.update_status(
            actor=actor, user_id=actor.id, status=UserStatus.DEACTIVATED
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "revokes"),
    [
        (UserStatus.SUSPENDED, True),
        (UserStatus.DEACTIVATED, True),
        (UserStatus.ACTIVE, False),
    ],
)
async def test_admin_status_lifecycle_revokes_sessions(
    status: UserStatus, revokes: bool
) -> None:
    actor = user(role=UserRole.SUPER_ADMIN, protected=True)
    target = user(role=UserRole.ADMIN)
    admin_service = service()
    admin_service.user_repository.get_by_id_for_update = AsyncMock(return_value=target)
    admin_service.session_repository.revoke_all_for_user = AsyncMock(return_value=2)

    result = await admin_service.update_status(
        actor=actor, user_id=target.id, status=status
    )

    assert result.status == status
    assert admin_service.session_repository.revoke_all_for_user.await_count == int(
        revokes
    )


@pytest.mark.asyncio
async def test_admin_demotion_preserves_credentials_and_revokes_sessions() -> None:
    actor = user(role=UserRole.SUPER_ADMIN, protected=True)
    target = user(role=UserRole.ADMIN, must_change_password=True)
    password_hash = target.password_hash
    admin_service = service()
    admin_service.user_repository.get_by_id_for_update = AsyncMock(return_value=target)
    admin_service.session_repository.revoke_all_for_user = AsyncMock(return_value=1)

    result = await admin_service.demote_admin(actor=actor, user_id=target.id)

    assert result.role == UserRole.USER
    assert result.must_change_password is False
    assert target.password_hash == password_hash
    admin_service.session_repository.revoke_all_for_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_to_admin_and_super_admin_role_changes_are_rejected() -> None:
    actor = user(role=UserRole.SUPER_ADMIN, protected=True)
    target = user(role=UserRole.USER)
    admin_service = service()
    admin_service.user_repository.get_by_id_for_update = AsyncMock(return_value=target)
    with pytest.raises(InvalidAdminRoleChangeError):
        await admin_service.demote_admin(actor=actor, user_id=target.id)
    with pytest.raises(InvalidAdminStatusError):
        await admin_service.delete_admin(actor=actor, user_id=target.id)
