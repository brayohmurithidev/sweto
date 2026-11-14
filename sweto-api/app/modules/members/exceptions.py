class MemberError(Exception):
    """Base class for gym-member errors."""


class GymMemberNotFoundError(MemberError):
    """The member does not exist in this gym."""


class GymMemberPhoneTakenError(MemberError):
    """Another member of this gym already has the phone number."""


class GymMemberArchivedError(MemberError):
    """The action needs an active member."""


class InvalidMembershipPaymentError(MemberError):
    """A cash payment cannot be recorded as asked."""
