from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends

from app.modules.admin.exceptions import PlatformRoleRequiredError
from app.modules.auth.dependencies import AuthContext, CurrentAuthContext
from app.modules.auth.enums import UserRole
from app.modules.auth.models import User


def require_platform_roles(
    *allowed_roles: UserRole,
) -> Callable[[AuthContext], Awaitable[User]]:
    """Build a dependency that checks the already-loaded platform role."""

    async def dependency(auth_context: CurrentAuthContext) -> User:
        if auth_context.user.role not in allowed_roles:
            raise PlatformRoleRequiredError(
                "Your platform role does not permit this operation."
            )
        return auth_context.user

    return dependency


SuperAdminUser = Annotated[
    User,
    Depends(require_platform_roles(UserRole.SUPER_ADMIN)),
]
