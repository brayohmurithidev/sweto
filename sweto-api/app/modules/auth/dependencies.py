from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.modules.auth.enums import UserStatus
from app.modules.auth.exceptions import (
    InvalidAccessTokenError,
    PasswordChangeRequiredError,
    UserAccessDeniedError,
)
from app.modules.auth.models import RefreshSession, User
from app.modules.auth.repository import (
    RefreshSessionRepository,
    UserRepository,
)
from app.modules.auth.tokens import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]

ApplicationSettings = Annotated[
    Settings,
    Depends(get_settings),
]

BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Authenticated user and the session used for this request."""

    user: User
    session: RefreshSession


async def get_current_auth_context(
    credentials: BearerCredentials,
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> AuthContext:
    """Validate the access token, session and user."""

    if credentials is None:
        raise InvalidAccessTokenError("Authentication credentials were not provided.")

    if credentials.scheme.lower() != "bearer":
        raise InvalidAccessTokenError("The authorization scheme must be Bearer.")

    claims = decode_access_token(
        token=credentials.credentials,
        settings=settings,
    )

    session_repository = RefreshSessionRepository(session)

    refresh_session = await session_repository.get_active_by_id(
        session_id=claims.session_id,
        user_id=claims.user_id,
    )

    if refresh_session is None:
        raise InvalidAccessTokenError("The authentication session is no longer active.")

    user_repository = UserRepository(session)

    user = await user_repository.get_by_id(claims.user_id)

    if user is None:
        raise InvalidAccessTokenError("The authenticated user no longer exists.")

    if user.status in {
        UserStatus.SUSPENDED,
        UserStatus.DEACTIVATED,
    }:
        raise UserAccessDeniedError("This account is not permitted to access SWETO.")

    now = datetime.now(UTC)

    stale_before = now - timedelta(
        seconds=settings.session_activity_update_interval_seconds
    )

    await session_repository.touch_session_if_stale(
        session_id=refresh_session.id,
        now=now,
        stale_before=stale_before,
    )

    await session.commit()

    return AuthContext(
        user=user,
        session=refresh_session,
    )


BaseAuthContext = Annotated[
    AuthContext,
    Depends(get_current_auth_context),
]


async def require_password_change_complete(
    auth_context: BaseAuthContext,
) -> AuthContext:
    """Require an authenticated user to have completed password setup."""

    if auth_context.user.must_change_password:
        raise PasswordChangeRequiredError(
            "Change your temporary password before accessing this resource."
        )

    return auth_context


CurrentAuthContext = Annotated[
    AuthContext,
    Depends(require_password_change_complete),
]


async def get_base_current_user(
    auth_context: BaseAuthContext,
) -> User:
    """Return a user without enforcing the forced-password gate."""

    return auth_context.user


BaseCurrentUser = Annotated[
    User,
    Depends(get_base_current_user),
]


async def get_current_user(
    auth_context: CurrentAuthContext,
) -> User:
    """Return only the user from the authenticated context."""

    return auth_context.user


CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]
