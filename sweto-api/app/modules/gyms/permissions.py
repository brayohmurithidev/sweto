"""What each gym staff role may do.

Every gym endpoint checks one of these permissions, and the app reads the
same list to decide which tabs and buttons to show. Change access here,
not in the services.
"""

from enum import StrEnum

from app.modules.gyms.enums import GymStaffRole


class GymPermission(StrEnum):
    """An action a gym staff member may be allowed to take."""

    VIEW_GYM = "view_gym"
    EDIT_GYM = "edit_gym"
    MANAGE_VERIFICATION = "manage_verification"
    MANAGE_PAYMENT_SETTINGS = "manage_payment_settings"
    MANAGE_STAFF = "manage_staff"
    VIEW_FINANCE = "view_finance"
    VIEW_ACTIVITY = "view_activity"
    VIEW_MEMBERS = "view_members"
    EDIT_MEMBERS = "edit_members"
    ARCHIVE_MEMBERS = "archive_members"
    TAKE_PAYMENTS = "take_payments"
    ISSUE_CHECK_IN_CODES = "issue_check_in_codes"
    CHECK_IN = "check_in"


_FRONT_DESK = frozenset(
    {
        GymPermission.VIEW_GYM,
        GymPermission.VIEW_MEMBERS,
        GymPermission.EDIT_MEMBERS,
        GymPermission.TAKE_PAYMENTS,
        GymPermission.ISSUE_CHECK_IN_CODES,
        GymPermission.CHECK_IN,
    }
)

_MANAGER = _FRONT_DESK | {
    GymPermission.EDIT_GYM,
    GymPermission.VIEW_FINANCE,
    # Who did what: for whoever answers for the till and the door.
    GymPermission.VIEW_ACTIVITY,
    GymPermission.ARCHIVE_MEMBERS,
}

ROLE_PERMISSIONS: dict[GymStaffRole, frozenset[GymPermission]] = {
    GymStaffRole.OWNER: frozenset(GymPermission),
    GymStaffRole.MANAGER: frozenset(_MANAGER),
    GymStaffRole.RECEPTIONIST: _FRONT_DESK,
    GymStaffRole.TRAINER: frozenset(
        {
            GymPermission.VIEW_GYM,
            GymPermission.VIEW_MEMBERS,
            GymPermission.CHECK_IN,
        }
    ),
}

# Roles an owner can give someone they add. Ownership is never handed out
# from the staff screen.
ASSIGNABLE_ROLES = frozenset(
    {GymStaffRole.MANAGER, GymStaffRole.RECEPTIONIST, GymStaffRole.TRAINER}
)

DENIED_MESSAGES: dict[GymPermission, str] = {
    GymPermission.VIEW_GYM: "You do not have access to this gym.",
    GymPermission.EDIT_GYM: "Only the gym's owner or a manager can change the gym.",
    GymPermission.MANAGE_VERIFICATION: (
        "Only the gym's owner can manage verification documents."
    ),
    GymPermission.MANAGE_PAYMENT_SETTINGS: (
        "Only the gym's owner can change where M-Pesa payments go."
    ),
    GymPermission.MANAGE_STAFF: "Only the gym's owner can manage staff.",
    GymPermission.VIEW_FINANCE: (
        "Only the gym's owner or a manager can see the gym's finances."
    ),
    GymPermission.VIEW_ACTIVITY: (
        "Only the gym's owner or a manager can see who did what."
    ),
    GymPermission.VIEW_MEMBERS: "You do not have access to this gym's members.",
    GymPermission.EDIT_MEMBERS: "Your role cannot add or change members.",
    GymPermission.ARCHIVE_MEMBERS: (
        "Only the gym's owner or a manager can archive members."
    ),
    GymPermission.TAKE_PAYMENTS: "Your role cannot take payments.",
    GymPermission.ISSUE_CHECK_IN_CODES: "Your role cannot issue check-in codes.",
    GymPermission.CHECK_IN: "Your role cannot check members in.",
}


def permissions_for(role: GymStaffRole) -> frozenset[GymPermission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def role_can(role: GymStaffRole, permission: GymPermission) -> bool:
    return permission in permissions_for(role)
