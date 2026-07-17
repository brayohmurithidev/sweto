class ProfileError(Exception):
    """Base exception for profile and account setup failures."""


class AccountRoleAlreadyExistsError(ProfileError):
    """Raised when a user already has the requested account role."""


class AccountRoleNotFoundError(ProfileError):
    """Raised when a requested account role is unavailable."""


class InvalidDefaultRoleError(ProfileError):
    """Raised when the default role is not active for the user."""


class ProfileNotFoundError(ProfileError):
    """Raised when a requested user profile does not exist."""


class InvalidProfileUpdateError(ProfileError):
    """Raised when a profile update violates a business rule."""
