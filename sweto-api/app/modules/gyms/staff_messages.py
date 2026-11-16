"""SMS text for gym staff. Kept short: one SMS segment where possible."""

from app.modules.gyms.enums import GymStaffRole

ROLE_LABELS: dict[GymStaffRole, str] = {
    GymStaffRole.OWNER: "owner",
    GymStaffRole.MANAGER: "a manager",
    GymStaffRole.RECEPTIONIST: "a receptionist",
    GymStaffRole.TRAINER: "a trainer",
}


def staff_invite(*, gym_name: str, role: GymStaffRole) -> str:
    return (
        f"{gym_name} added you on SWETO as {ROLE_LABELS[role]}. "
        "Get the SWETO app and sign in with this phone number to start."
    )
