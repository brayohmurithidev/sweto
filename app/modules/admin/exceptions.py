class AdminError(Exception):
    """Base exception for platform administration failures."""


class AdminEmailAlreadyExistsError(AdminError):
    """Raised when an administrative email is already registered."""


class AdminNotFoundError(AdminError):
    """Raised when an administrative target does not exist."""


class PlatformRoleRequiredError(AdminError):
    """Raised when a platform role is insufficient."""


class ProtectedSystemUserError(AdminError):
    """Raised when a protected or Super Admin account would be altered."""


class SelfAdministrationNotAllowedError(AdminError):
    """Raised for destructive self-management."""


class InvalidAdminStatusError(AdminError):
    """Raised for unsupported administrative status transitions."""


class InvalidAdminRoleChangeError(AdminError):
    """Raised for unsupported platform-role transitions."""


class SuperAdminIntegrityError(AdminError):
    """Raised when the single protected Super Admin invariant is broken."""


class SuperAdminConfigurationError(AdminError):
    """Raised when explicit bootstrap configuration is invalid."""
