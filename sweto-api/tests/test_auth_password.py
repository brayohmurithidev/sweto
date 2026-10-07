from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import Settings
from app.database import models  # noqa: F401
from app.modules.auth import dependencies
from app.modules.auth.dependencies import (
    AuthContext,
    get_current_auth_context,
    require_password_change_complete,
)
from app.modules.auth.enums import SessionStatus, UserRole, UserStatus
from app.modules.auth.exceptions import (
    CurrentPasswordIncorrectError,
    InvalidAccessTokenError,
    InvalidEmailOrPasswordError,
    PasswordChangeRequiredError,
    PasswordPolicyViolationError,
    PasswordReuseNotAllowedError,
    RefreshSessionRevokedError,
    UserAccessDeniedError,
)
from app.modules.auth.models import RefreshSession, User
from app.modules.auth.router import get_me
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    PasswordLoginRequest,
    RefreshTokenRequest,
)
from app.modules.auth.security import hash_password, normalize_email, verify_password
from app.modules.auth.service import AuthenticationService
from app.modules.auth.tokens import hash_refresh_token
from app.rate_limit.memory import MemoryRateLimiter


def build_service(settings: Settings) -> AuthenticationService:
    session = Mock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return AuthenticationService(
        session=session,
        settings=settings,
        sms_provider=Mock(),
        rate_limiter=MemoryRateLimiter(),
    )


def password_user(
    *,
    password: str = "temporary-password",
    status: UserStatus = UserStatus.ACTIVE,
    must_change_password: bool = True,
) -> User:
    return User(
        id=uuid4(),
        phone_number=None,
        email="admin@example.com",
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
        status=status,
        is_phone_verified=False,
        must_change_password=must_change_password,
        is_system_protected=False,
    )


def test_normalize_email_strips_and_lowercases() -> None:
    assert normalize_email("  Admin@Example.COM ") == "admin@example.com"


def test_password_login_schema_normalizes_email() -> None:
    payload = PasswordLoginRequest(email="Admin@Example.COM", password="password")

    assert str(payload.email) == "admin@example.com"


def test_otp_user_defaults_keep_platform_user_role() -> None:
    user = User(phone_number="+254712345678")

    assert user.phone_number == "+254712345678"
    assert user.role is None or user.role == UserRole.USER
    assert user.email is None


def test_admin_style_user_can_have_no_phone() -> None:
    user = password_user()

    assert user.phone_number is None
    assert user.email == "admin@example.com"


@pytest.mark.asyncio
async def test_password_change_gate_blocks_normal_routes() -> None:
    user = password_user()
    auth_context = AuthContext(
        user=user,
        session=RefreshSession(
            id=uuid4(),
            user_id=user.id,
            token_hash="hash",
            status=SessionStatus.ACTIVE,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ),
    )

    with pytest.raises(PasswordChangeRequiredError):
        await require_password_change_complete(auth_context)


@pytest.mark.asyncio
async def test_me_remains_available_during_required_password_change() -> None:
    user = password_user()

    response = await get_me(user)

    assert response.data.id == user.id
    assert response.data.must_change_password is True


@pytest.mark.asyncio
async def test_password_login_success(settings: Settings) -> None:
    service = build_service(settings)
    user = password_user()
    service.user_repository.get_by_email = AsyncMock(return_value=user)
    service.refresh_session_repository.add = Mock(
        side_effect=lambda item: setattr(item, "id", uuid4())
    )

    result = await service.password_login(
        payload=PasswordLoginRequest(
            email="ADMIN@example.com",
            password="temporary-password",
        ),
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert result.user.id == user.id
    assert result.user.phone_number is None
    assert result.must_change_password is True
    assert result.tokens.access_token
    assert result.tokens.refresh_token


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_user", [None, password_user()])
async def test_password_login_uses_generic_invalid_credentials(
    settings: Settings,
    existing_user: User | None,
) -> None:
    service = build_service(settings)
    service.user_repository.get_by_email = AsyncMock(return_value=existing_user)

    with pytest.raises(InvalidEmailOrPasswordError) as error:
        await service.password_login(
            payload=PasswordLoginRequest(
                email="admin@example.com",
                password="wrong-password",
            ),
            ip_address=None,
            user_agent=None,
        )

    assert str(error.value) == "The email or password is incorrect."


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [UserStatus.SUSPENDED, UserStatus.DEACTIVATED])
async def test_password_login_blocks_disabled_users(
    settings: Settings,
    status: UserStatus,
) -> None:
    service = build_service(settings)
    service.user_repository.get_by_email = AsyncMock(
        return_value=password_user(status=status)
    )

    with pytest.raises(UserAccessDeniedError):
        await service.password_login(
            payload=PasswordLoginRequest(
                email="admin@example.com",
                password="temporary-password",
            ),
            ip_address=None,
            user_agent=None,
        )


@pytest.mark.asyncio
async def test_change_password_requires_current_password(settings: Settings) -> None:
    service = build_service(settings)
    user = password_user()
    service.user_repository.get_by_id_for_update = AsyncMock(return_value=user)

    with pytest.raises(CurrentPasswordIncorrectError):
        await service.change_password(
            user_id=user.id,
            payload=ChangePasswordRequest(
                current_password="wrong-password",
                new_password="a-new-secure-password",
            ),
            ip_address=None,
            user_agent=None,
        )


@pytest.mark.asyncio
async def test_change_password_rejects_reuse_and_weak_password(
    settings: Settings,
) -> None:
    service = build_service(settings)
    user = password_user()
    service.user_repository.get_by_id_for_update = AsyncMock(return_value=user)

    with pytest.raises(PasswordReuseNotAllowedError):
        await service.change_password(
            user_id=user.id,
            payload=ChangePasswordRequest(
                current_password="temporary-password",
                new_password="temporary-password",
            ),
            ip_address=None,
            user_agent=None,
        )

    with pytest.raises(PasswordPolicyViolationError):
        await service.change_password(
            user_id=user.id,
            payload=ChangePasswordRequest(
                current_password="temporary-password",
                new_password="too-short",
            ),
            ip_address=None,
            user_agent=None,
        )


@pytest.mark.asyncio
async def test_change_password_clears_flag_revokes_sessions_and_changes_secret(
    settings: Settings,
) -> None:
    service = build_service(settings)
    user = password_user()
    old_hash = user.password_hash
    service.user_repository.get_by_id_for_update = AsyncMock(return_value=user)
    service.refresh_session_repository.revoke_all_for_user = AsyncMock(return_value=2)

    result = await service.change_password(
        user_id=user.id,
        payload=ChangePasswordRequest(
            current_password="temporary-password",
            new_password="a-new-secure-password",
        ),
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert result.sessions_revoked == 2
    assert user.must_change_password is False
    assert user.password_hash != old_hash
    assert not verify_password("temporary-password", user.password_hash or "")
    assert verify_password("a-new-secure-password", user.password_hash or "")
    service.refresh_session_repository.revoke_all_for_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_password_change_invalidates_old_tokens_and_credentials(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = build_service(settings)
    user = password_user()
    service.user_repository.get_by_email = AsyncMock(return_value=user)
    sessions: list[RefreshSession] = []

    def add_session(item: RefreshSession) -> None:
        item.id = uuid4()
        sessions.append(item)

    service.refresh_session_repository.add = Mock(side_effect=add_session)
    first_login = await service.password_login(
        payload=PasswordLoginRequest(
            email="admin@example.com",
            password="temporary-password",
        ),
        ip_address=None,
        user_agent=None,
    )
    old_session = sessions[0]
    service.user_repository.get_by_id_for_update = AsyncMock(return_value=user)

    async def revoke_sessions(**_: object) -> int:
        for item in sessions:
            item.status = SessionStatus.REVOKED
        return len(sessions)

    service.refresh_session_repository.revoke_all_for_user = AsyncMock(
        side_effect=revoke_sessions
    )
    await service.change_password(
        user_id=user.id,
        payload=ChangePasswordRequest(
            current_password="temporary-password",
            new_password="a-new-secure-password",
        ),
        ip_address=None,
        user_agent=None,
    )

    class FakeSessionRepository:
        def __init__(self, _: object) -> None:
            pass

        async def get_active_by_id(self, **_: object) -> RefreshSession | None:
            return None

    monkeypatch.setattr(dependencies, "RefreshSessionRepository", FakeSessionRepository)
    with pytest.raises(InvalidAccessTokenError):
        await get_current_auth_context(
            HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=first_login.tokens.access_token,
            ),
            AsyncMock(),
            settings,
        )

    service.refresh_session_repository.get_by_token_hash_for_update = AsyncMock(
        return_value=old_session
    )
    with pytest.raises(RefreshSessionRevokedError):
        await service.refresh_tokens(
            payload=RefreshTokenRequest(
                refresh_token=first_login.tokens.refresh_token,
            ),
            ip_address=None,
            user_agent=None,
        )
    assert old_session.token_hash == hash_refresh_token(
        first_login.tokens.refresh_token
    )

    with pytest.raises(InvalidEmailOrPasswordError):
        await service.password_login(
            payload=PasswordLoginRequest(
                email="admin@example.com",
                password="temporary-password",
            ),
            ip_address=None,
            user_agent=None,
        )
    second_login = await service.password_login(
        payload=PasswordLoginRequest(
            email="admin@example.com",
            password="a-new-secure-password",
        ),
        ip_address=None,
        user_agent=None,
    )
    assert second_login.tokens.access_token
